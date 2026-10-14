from app.citations import validate_claims
from app.graph.schemas import Claim

EVIDENCE = [{"source_id": "S1"}, {"source_id": "S2"}]


def claim(ids):
    return Claim(text="A sufficiently long claim.", source_ids=ids)


def test_valid_claims_kept():
    valid, problems = validate_claims([claim(["S1"]), claim(["S1", "S2"])], EVIDENCE)
    assert len(valid) == 2 and problems == []


def test_unknown_id_drops_claim():
    valid, problems = validate_claims([claim(["S1"]), claim(["S9"])], EVIDENCE)
    assert len(valid) == 1 and "S9" in problems[0]


def test_partially_unknown_ids_still_drop_claim():
    valid, problems = validate_claims([claim(["S1", "S9"])], EVIDENCE)
    assert valid == [] and len(problems) == 1