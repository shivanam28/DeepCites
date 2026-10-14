import pytest
from pydantic import BaseModel

from app import structured
from app.llm import LLMError


class Tiny(BaseModel):
    x: int


def fake(replies):
    it = iter(replies)
    return lambda messages, **kwargs: next(it)


def test_valid_json(monkeypatch):
    monkeypatch.setattr(structured, "complete", fake(['{"x": 1}']))
    assert structured.complete_structured([], Tiny).x == 1


def test_json_wrapped_in_prose_and_fence(monkeypatch):
    monkeypatch.setattr(structured, "complete", fake(['Sure!\n```json\n{"x": 2}\n```']))
    assert structured.complete_structured([], Tiny).x == 2


def test_retry_then_success(monkeypatch):
    monkeypatch.setattr(structured, "complete", fake(["not json", '{"x": 3}']))
    assert structured.complete_structured([], Tiny).x == 3


def test_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(structured, "complete", fake(["nope", '{"x": "abc"}']))
    with pytest.raises(LLMError):
        structured.complete_structured([], Tiny)