import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from app import store
from app.auth import AuthUser, get_current_user
from app.store import StoreError
from app.uploads import MAX_UPLOAD_BYTES, UploadError, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter()
MULTIPART_OVERHEAD = 64 * 1024


@router.post("/documents", status_code=201)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
):
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD:
        raise HTTPException(status_code=413, detail="File is too large (10 MB maximum).")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)  # never read more than the limit plus one byte
    try:
        v = validate_upload(file.filename or "", data)
    except UploadError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)

    doc_id = str(uuid.uuid4())
    path = f"{user.id}/{doc_id}{v.ext}"  # our own name; the original is kept only for display
    row = {"id": doc_id, "filename": v.filename, "storage_path": path,
           "mime_type": v.mime, "size_bytes": v.size}  # user_id is filled in by the database
    try:
        doc = store.insert_document(user, row)
    except StoreError:
        raise HTTPException(status_code=502, detail="Could not save the document.")
    try:
        store.upload_object(user, path, data, v.mime)
    except StoreError:
        try:
            store.delete_document_row(user, doc_id)
        except StoreError:
            logger.error("Orphan document row left behind: %s", doc_id)
        raise HTTPException(status_code=502, detail="Could not store the file.")
    return {"id": doc["id"], "filename": doc["filename"],
            "size_bytes": doc["size_bytes"], "status": doc["status"]}


@router.get("/documents")
def list_documents(user: AuthUser = Depends(get_current_user)):
    try:
        return store.list_documents(user)
    except StoreError:
        raise HTTPException(status_code=502, detail="Could not load documents.")


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: uuid.UUID, user: AuthUser = Depends(get_current_user)):
    try:
        doc = store.get_document(user, str(doc_id))
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        store.delete_object(user, doc["storage_path"])
        store.delete_document_row(user, str(doc_id))
    except StoreError:
        raise HTTPException(status_code=502, detail="Could not delete the document.")
    return Response(status_code=204)