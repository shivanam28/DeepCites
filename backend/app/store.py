import logging

import httpx

from app.auth import AuthUser
from app.config import get_settings

logger = logging.getLogger(__name__)
BUCKET = "documents"
TIMEOUT = 30.0


class StoreError(Exception):
    def __init__(self, status: int | None = None):
        super().__init__(f"store error (HTTP {status})" if status else "store error")
        self.status = status


def _request(method: str, url: str, user: AuthUser, *, extra_headers=None, **kwargs):
    headers = {
        "apikey": get_settings().supabase_publishable_key,
        "Authorization": f"Bearer {user.token}",  # the user's own token: RLS applies
        **(extra_headers or {}),
    }
    try:
        return httpx.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
    except httpx.HTTPError as exc:
        logger.warning("Supabase request failed: %s", type(exc).__name__)
        raise StoreError() from None


def _fail(what: str, r) -> None:
    logger.warning("%s failed: HTTP %s", what, r.status_code)
    raise StoreError(r.status_code)


def _rest() -> str:
    return get_settings().supabase_url.rstrip("/") + "/rest/v1"


def _objects() -> str:
    return get_settings().supabase_url.rstrip("/") + f"/storage/v1/object/{BUCKET}"


def insert_document(user: AuthUser, row: dict) -> dict:
    r = _request("POST", f"{_rest()}/documents", user,
                 extra_headers={"Prefer": "return=representation"}, json=row)
    if r.status_code != 201:
        _fail("Insert document", r)
    return r.json()[0]


def list_documents(user: AuthUser) -> list[dict]:
    r = _request("GET", f"{_rest()}/documents", user, params={
        "select": "id,filename,size_bytes,status,created_at",
        "order": "created_at.desc", "limit": "100"})
    if r.status_code != 200:
        _fail("List documents", r)
    return r.json()


def get_document(user: AuthUser, doc_id: str) -> dict | None:
    r = _request("GET", f"{_rest()}/documents", user,
                 params={"id": f"eq.{doc_id}", "select": "id,storage_path"})
    if r.status_code != 200:
        _fail("Get document", r)
    rows = r.json()
    return rows[0] if rows else None


def delete_document_row(user: AuthUser, doc_id: str) -> None:
    r = _request("DELETE", f"{_rest()}/documents", user, params={"id": f"eq.{doc_id}"})
    if r.status_code not in (200, 204):
        _fail("Delete document row", r)


def upload_object(user: AuthUser, path: str, data: bytes, mime: str) -> None:
    r = _request("POST", f"{_objects()}/{path}", user, content=data,
                 extra_headers={"Content-Type": mime, "x-upsert": "false"})
    if r.status_code != 200:
        _fail("Upload object", r)


def delete_object(user: AuthUser, path: str) -> None:
    r = _request("DELETE", f"{_objects()}/{path}", user)
    if r.status_code not in (200, 404):
        _fail("Delete object", r)