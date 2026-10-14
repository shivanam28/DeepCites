from app.graph import nodes
from app.graph.schemas import Answer, Claim
from app.llm import LLMError

EVIDENCE = [
    {"source_id": "S1", "title": "T1", "url": "https://a.example", "snippet": "alpha"},
    {"source_id": "S2", "title": "T2", "url": "https://b.example", "snippet": "beta"},
]


def boom(*args, **kwargs):
    raise AssertionError("LLM must not be called")


def answer_with(*claims, limitations=""):
    return Answer(claims=list(claims), limitations=limitations)


def test_no_evidence_skips_llm(monkeypatch):
    monkeypatch.setattr(nodes, "complete_structured", boom)
    out = nodes.writer({"question": "q", "evidence": []})
    assert out["answer"] == nodes.INSUFFICIENT and out["claims"] == []


def test_valid_claim_rendered_with_sources(monkeypatch):
    c = Claim(text="Alpha is true according to the source.", source_ids=["S1"])
    monkeypatch.setattr(nodes, "complete_structured", lambda *a, **k: answer_with(c))
    out = nodes.writer({"question": "q", "evidence": EVIDENCE})
    assert "[S1]" in out["answer"] and "https://a.example" in out["answer"]
    assert "https://b.example" not in out["answer"]  # only cited sources are listed


def test_invalid_id_is_dropped_and_reported(monkeypatch):
    good = Claim(text="Alpha is true according to the source.", source_ids=["S1"])
    bad = Claim(text="Gamma is made up by the model.", source_ids=["S7"])
    monkeypatch.setattr(nodes, "complete_structured", lambda *a, **k: answer_with(good, bad))
    out = nodes.writer({"question": "q", "evidence": EVIDENCE})
    assert len(out["claims"]) == 1 and "S7" in out["citation_problems"][0]
    assert "made up" not in out["answer"]


def test_only_invalid_claims_gives_insufficient(monkeypatch):
    bad = Claim(text="Gamma is made up by the model.", source_ids=["S7"])
    monkeypatch.setattr(nodes, "complete_structured", lambda *a, **k: answer_with(bad))
    out = nodes.writer({"question": "q", "evidence": EVIDENCE})
    assert out["answer"].startswith(nodes.INSUFFICIENT)


def test_llm_failure_falls_back_to_sources(monkeypatch):
    def fail(*a, **k):
        raise LLMError("HTTP 503")

    monkeypatch.setattr(nodes, "complete_structured", fail)
    out = nodes.writer({"question": "q", "evidence": EVIDENCE})
    assert "Sources found" in out["answer"] and out["claims"] == []