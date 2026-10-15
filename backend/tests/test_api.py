import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import research

app = FastAPI()
app.include_router(research.router)
client = TestClient(app)

from app.auth import AuthUser, get_current_user

app.dependency_overrides[get_current_user] = lambda: AuthUser(id="test-user", email=None)

STATES = [
    {"question": "q"},
    {"question": "q", "trace": ["planner (llm)"]},
    {
        "question": "q",
        "trace": ["planner (llm)", "writer (1 claims drafted)"],
        "answer": "An answer. [S1]",
        "claims": [],
        "claim_checks": [],
        "evidence": [{"source_id": "S1", "title": "T", "url": "https://a.example", "snippet": "SECRET"}],
    },
]


class FakeGraph:
    def __init__(self, states=None, error=None):
        self.states, self.error = states or [], error

    def stream(self, inputs, stream_mode):
        if self.error:
            raise self.error
        yield from self.states


def parse(text: str):
    events = []
    for block in text.strip().split("\n\n"):
        event_line, data_line = block.split("\n", 1)
        events.append((event_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


def test_rejects_invalid_questions():
    for bad in ["", "   ", "ab", "x" * 501]:
        assert client.post("/research", json={"question": bad}).status_code == 422
    assert client.post("/research", json={}).status_code == 422


def test_streams_progress_then_result(monkeypatch):
    monkeypatch.setattr(research, "graph", FakeGraph(STATES))
    for _ in range(3):  # three runs in a row also proves slots are released
        r = client.post("/research", json={"question": "valid question"})
        events = parse(r.text)
        assert [e[0] for e in events] == ["progress", "progress", "result"]
        assert events[2][1]["sources"][0]["url"] == "https://a.example"
        assert "SECRET" not in r.text  # snippets never leave the server


def test_failure_hides_internal_details(monkeypatch):
    monkeypatch.setattr(research, "graph", FakeGraph(error=RuntimeError("secret-detail")))
    r = client.post("/research", json={"question": "valid question"})
    events = parse(r.text)
    assert events[0][0] == "error" and events[0][1]["code"] == "failed"
    assert "secret-detail" not in r.text


def test_busy_when_all_slots_taken(monkeypatch):
    monkeypatch.setattr(research, "graph", FakeGraph(STATES))
    research._slots.acquire()
    research._slots.acquire()
    try:
        r = client.post("/research", json={"question": "valid question"})
        assert parse(r.text)[0][1]["code"] == "busy"
    finally:
        research._slots.release()
        research._slots.release()


def test_research_requires_login():
    locked = FastAPI()
    locked.include_router(research.router)
    r = TestClient(locked).post("/research", json={"question": "valid question"})
    assert r.status_code == 401