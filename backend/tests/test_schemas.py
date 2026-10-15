import pytest
from pydantic import ValidationError

from app.graph.schemas import Answer, Claim


def test_overlong_limitations_is_trimmed_not_rejected():
    a = Answer(claims=[], limitations="x" * 2000)
    assert len(a.limitations) <= 600


def test_overlong_claim_is_still_rejected():
    with pytest.raises(ValidationError):
        Claim(text="x" * 700, source_ids=["S1"])


def test_malformed_source_id_is_still_rejected():
    with pytest.raises(ValidationError):
        Claim(text="A sufficiently long claim.", source_ids=["[S1]"])