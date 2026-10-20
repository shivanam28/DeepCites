import pytest

from app import pipeline
from app.auth import AuthUser

USER = AuthUser(id="u1", email=None, token="t")
TEXT = ("A sentence about retrieval. " * 40 + "\n\n") * 4  # several chunks


class FakeStore:
    def __init__(self, data=TEXT.encode(), path="u1/d1.txt", exists=True):
        self.data, self.path, self.exists = data, path, exists
        self.updates, self.inserted, self.chunk_deletes = [], [], 0

    def get_document(self, user, doc_id):
        return {"id": doc_id, "storage_path": self.path, "status": "uploaded"} if self.exists else None

    def update_document(self, user, doc_id, fields):
        self.updates.append(fields)

    def download_object(self, user, path):
        return self.data

    def delete_chunks(self, user, doc_id):
        self.chunk_deletes += 1

    def insert_chunks(self, user, rows):
        self.inserted.extend(rows)


def run(monkeypatch, fake, embed=None):
    monkeypatch.setattr(pipeline, "store", fake)
    monkeypatch.setattr(pipeline, "embed_passages", embed or (lambda texts: [[0.1] * 384 for _ in texts]))
    return pipeline.process_document(USER, "d1")


def test_success_stores_chunks_and_marks_ready(monkeypatch):
    fake = FakeStore()
    out = run(monkeypatch, fake)
    assert out["status"] == "ready" and out["chunk_count"] == len(fake.inserted) > 1
    assert fake.updates[0]["status"] == "processing" and fake.updates[-1]["status"] == "ready"
    assert [r["chunk_index"] for r in fake.inserted] == list(range(len(fake.inserted)))
    assert fake.inserted[0]["embedding"].count(",") == 383


def test_unreadable_pdf_is_recorded_as_failed(monkeypatch):
    fake = FakeStore(data=b"%PDF-1.4 not really a pdf", path="u1/d1.pdf")
    out = run(monkeypatch, fake)
    assert out["status"] == "failed" and "PDF" in out["status_detail"]
    assert fake.inserted == [] and fake.chunk_deletes >= 1 and fake.updates[-1]["status"] == "failed"


def test_unexpected_error_hides_details(monkeypatch):
    def boom(texts):
        raise RuntimeError("secret-internal-detail")

    fake = FakeStore()
    out = run(monkeypatch, fake, embed=boom)
    assert out["status"] == "failed" and "secret-internal-detail" not in str(out)
    assert fake.chunk_deletes >= 1


def test_unknown_document(monkeypatch):
    with pytest.raises(LookupError):
        run(monkeypatch, FakeStore(exists=False))