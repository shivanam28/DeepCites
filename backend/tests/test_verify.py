from app import verify
from app.graph import nodes

QUESTION = "Does time-restricted eating work?"
EVIDENCE = [
    {
        "source_id": "S1",
        "title": "Trial results",
        "url": "https://a.example",
        "snippet": "In a randomized trial, participants lost 5 kg over 12 weeks with "
        "time-restricted eating compared with calorie counting.",
    }
]
BY_ID = {e["source_id"]: e for e in EVIDENCE}


def claim(text):
    return {"text": text, "source_ids": ["S1"]}


def test_supported_claim_is_ok():
    r = verify.check_claim(claim("Participants in a randomized trial lost weight over 12 weeks."), QUESTION, BY_ID)
    assert r["verdict"] == "ok" and r["missing_numbers"] == []


def test_number_not_in_source_is_unsupported():
    r = verify.check_claim(claim("Participants lost 9 kg in the trial."), QUESTION, BY_ID)
    assert r["verdict"] == "unsupported" and r["missing_numbers"] == ["9"]


def test_unrelated_claim_is_weak():
    r = verify.check_claim(claim("The Mediterranean diet reduces cardiovascular mortality significantly."), QUESTION, BY_ID)
    assert r["verdict"] == "weak"


def test_topic_words_do_not_inflate_overlap():
    r = verify.check_claim(claim("Time-restricted eating works for people."), QUESTION, BY_ID)
    assert r["overlap"] == 0.0 and r["verdict"] == "weak"


def state_with(*claims):
    return {"question": QUESTION, "evidence": EVIDENCE, "claims": list(claims), "limitations": ""}


def test_verifier_drops_unsupported_and_rerenders():
    good = claim("Participants in a randomized trial lost weight over 12 weeks.")
    bad = claim("Participants lost 9 kg in the trial.")
    out = nodes.verifier(state_with(good, bad))
    assert len(out["claims"]) == 1 and "9 kg" not in out["answer"]


def test_verifier_marks_weak_claims():
    weak = claim("The Mediterranean diet reduces cardiovascular mortality significantly.")
    out = nodes.verifier(state_with(weak))
    assert "[weak support]" in out["answer"]


def test_verifier_leaves_existing_answer_when_no_claims():
    out = nodes.verifier({"question": QUESTION, "evidence": EVIDENCE, "claims": []})
    assert "answer" not in out