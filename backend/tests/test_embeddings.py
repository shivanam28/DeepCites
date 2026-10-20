import pytest

from app import embeddings


class FakeModel:
    def __init__(self, dim=384):
        self.dim = dim

    def passage_embed(self, texts):
        return iter([[0.5] * self.dim for _ in texts])

    def query_embed(self, text):
        return iter([[0.25] * self.dim])


def test_passages_and_query_have_expected_dimension(monkeypatch):
    monkeypatch.setattr(embeddings, "_load", lambda: FakeModel())
    assert len(embeddings.embed_passages(["a", "b"])) == 2
    assert len(embeddings.embed_query("q")) == embeddings.DIMENSIONS


def test_wrong_dimension_is_rejected(monkeypatch):
    monkeypatch.setattr(embeddings, "_load", lambda: FakeModel(dim=768))
    with pytest.raises(RuntimeError):
        embeddings.embed_passages(["a"])