import json
import logging
import threading
from typing import Annotated, Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints
from app.auth import AuthUser, get_current_user

from app.graph.builder import build_graph

logger = logging.getLogger(__name__)
router = APIRouter()

graph = build_graph()  # compiled once, at import time
_slots = threading.BoundedSemaphore(2)  # at most 2 research runs at the same time


class ResearchRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run(question: str) -> Iterator[str]:
    if not _slots.acquire(blocking=False):
        yield _sse("error", {"code": "busy", "message": "Server is busy. Try again shortly."})
        return
    try:
        seen = 0
        final: dict = {}
        for state in graph.stream({"question": question}, stream_mode="values"):
            final = state
            trace = state.get("trace", [])
            for step in trace[seen:]:
                yield _sse("progress", {"step": step})
            seen = len(trace)

        sources = [
            {"source_id": e["source_id"], "title": e["title"], "url": e["url"]}
            for e in final.get("evidence", [])
        ]
        yield _sse(
            "result",
            {
                "answer": final.get("answer", ""),
                "claims": final.get("claims", []),
                "claim_checks": final.get("claim_checks", []),
                "sources": sources,  # no snippets: the client only needs links
            },
        )
    except Exception as exc:
        logger.error("Research run failed: %s", type(exc).__name__)
        yield _sse("error", {"code": "failed", "message": "Research failed. Please try again."})
    finally:
        _slots.release()


@router.post("/research")
def research(req: ResearchRequest, _user: AuthUser = Depends(get_current_user)):
    return StreamingResponse(
        _run(req.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )