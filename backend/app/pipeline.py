import logging
import os

from app import store
from app.auth import AuthUser
from app.embeddings import embed_passages
from app.ingest import IngestError, chunk_text, extract_text
from app.store import StoreError

logger = logging.getLogger(__name__)
INSERT_BATCH = 50


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


def _summary(doc_id, status, count=0, truncated=False, detail=None) -> dict:
    return {"id": doc_id, "status": status, "chunk_count": count,
            "truncated": truncated, "status_detail": detail}


def _record_failure(user: AuthUser, doc_id: str, detail: str) -> dict:
    try:
        store.delete_chunks(user, doc_id)  # a failed document must leave nothing searchable
        store.update_document(user, doc_id, {"status": "failed", "status_detail": detail,
                                             "chunk_count": 0, "truncated": False})
    except StoreError:
        logger.error("Could not record failure for document %s", doc_id)
    return _summary(doc_id, "failed", detail=detail)


def process_document(user: AuthUser, doc_id: str) -> dict:
    doc = store.get_document(user, doc_id)
    if doc is None:
        raise LookupError(doc_id)
    store.update_document(user, doc_id, {"status": "processing", "status_detail": None})

    try:
        data = store.download_object(user, doc["storage_path"])
        extracted = extract_text(data, os.path.splitext(doc["storage_path"])[1].lower())
        chunks, chunks_truncated = chunk_text(extracted.text)
        vectors = embed_passages(chunks)

        store.delete_chunks(user, doc_id)  # re-processing replaces any earlier chunks
        for start in range(0, len(chunks), INSERT_BATCH):
            stop = min(start + INSERT_BATCH, len(chunks))
            store.insert_chunks(user, [
                {"document_id": doc_id, "chunk_index": i, "content": chunks[i],
                 "embedding": _vector_literal(vectors[i])}
                for i in range(start, stop)
            ])

        truncated = extracted.truncated or chunks_truncated
        detail = None
        if extracted.low_text:
            detail = (f"Very little text was found ({len(extracted.text)} characters). This may be a "
                      "scanned or image-based document; images are not indexed.")
        elif truncated:
            detail = "Only the first part of this document was indexed (size limits)."
        store.update_document(user, doc_id, {"status": "ready", "status_detail": detail,
                                             "chunk_count": len(chunks), "truncated": truncated})
        return _summary(doc_id, "ready", len(chunks), truncated, detail)
    except IngestError as exc:  # our own messages, safe to show the user
        return _record_failure(user, doc_id, str(exc))
    except Exception as exc:
        logger.error("Processing failed for document %s: %s", doc_id, type(exc).__name__)
        return _record_failure(user, doc_id, "Processing failed. Please try again.")