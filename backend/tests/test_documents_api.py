from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import AuthUser, get_current_user
from app.routes import documents
from app.store import StoreError
from app.uploads import MAX_UPLOAD_BYTES

app = FastAPI()
app.include_router(documents.router)
app.dependency_overrides[get_current_user] = lambda: AuthUser(id="u1", email=None, token="t")
client = TestClient(app)


class FakeStore:
    def __init__(self, fail_upload=False, existing=None):
        self.calls, self.fail_upload, self.existing = [], fail_upload, existing

    def insert_document(self, user, row):
        self.calls.append(("insert", row))
        return {**row, "status": "uploaded"}

    def upload_object(self, user, path, data, mime):
        self.calls.append(("upload", path))
        if self.fail_upload:
            raise StoreError(500)

    def delete_document_row(self, user, doc_id):
        self.calls.append(("delete_row", doc_id))

    def delete_object(self, user, path):
        self.calls.append(("delete_object", path))

    def get_document(self, user, doc_id):
        return self.existing


def post(name="a.txt", data=b"hello"):
    return client.post("/documents", files={"file": (name, data, "text/plain")})


def test_upload_success(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(documents, "store", fake)
    r = post()
    assert r.status_code == 201
    assert [c[0] for c in fake.calls] == ["insert", "upload"]
    row = fake.calls[0][1]
    assert row["storage_path"].startswith("u1/") and row["storage_path"].endswith(".txt")
    assert "user_id" not in row  # ownership comes from the token, never from the request


def test_invalid_file_never_touches_storage(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(documents, "store", fake)
    assert post("run.exe").status_code == 415
    assert fake.calls == []


def test_oversized_file_is_413(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(documents, "store", fake)
    assert post("big.txt", b"a" * (MAX_UPLOAD_BYTES + 1)).status_code == 413
    assert fake.calls == []


def test_storage_failure_cleans_up_row(monkeypatch):
    fake = FakeStore(fail_upload=True)
    monkeypatch.setattr(documents, "store", fake)
    assert post().status_code == 502
    assert [c[0] for c in fake.calls] == ["insert", "upload", "delete_row"]


def test_delete_unknown_document_is_404(monkeypatch):
    fake = FakeStore(existing=None)
    monkeypatch.setattr(documents, "store", fake)
    r = client.delete("/documents/3f2b8c1e-0000-4000-8000-000000000001")
    assert r.status_code == 404 and fake.calls == []


def test_delete_with_invalid_id_is_422():
    assert client.delete("/documents/not-a-uuid").status_code == 422


def test_requires_login():
    locked = FastAPI()
    locked.include_router(documents.router)
    r = TestClient(locked).post("/documents", files={"file": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 401

class FakePipeline:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def process_document(self, user, doc_id):
        if self.error:
            raise self.error
        return self.result


DOC = "/documents/3f2b8c1e-0000-4000-8000-000000000001/process"


def test_process_returns_summary(monkeypatch):
    summary = {"id": "x", "status": "ready", "chunk_count": 3, "truncated": False, "status_detail": None}
    monkeypatch.setattr(documents, "pipeline", FakePipeline(result=summary))
    r = client.post(DOC)
    assert r.status_code == 200 and r.json()["chunk_count"] == 3


def test_process_unknown_document_is_404(monkeypatch):
    monkeypatch.setattr(documents, "pipeline", FakePipeline(error=LookupError("x")))
    assert client.post(DOC).status_code == 404


def test_process_busy_is_429(monkeypatch):
    monkeypatch.setattr(documents, "pipeline", FakePipeline(result={}))
    documents._process_slots.acquire()
    try:
        assert client.post(DOC).status_code == 429
    finally:
        documents._process_slots.release()


def test_process_invalid_id_is_422():
    assert client.post("/documents/not-a-uuid/process").status_code == 422