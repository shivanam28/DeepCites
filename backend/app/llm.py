import logging
import threading
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 60.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_lock = threading.Lock()
_last_call = 0.0


class LLMError(Exception):
    pass


def _throttle(max_rpm: int) -> None:
    """Space calls at least 60/max_rpm seconds apart."""
    global _last_call
    with _lock:
        wait = _last_call + 60.0 / max_rpm - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def complete(messages: list[dict], *, max_tokens: int = 1024, temperature: float = 0.2) -> str:
    s = get_settings()
    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {s.llm_api_key}"}
    payload = {
        "model": s.llm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    last_error = "unknown"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _throttle(s.llm_max_rpm)
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            last_error = type(exc).__name__
        else:
            if r.status_code == 200:
                try:
                    return r.json()["choices"][0]["message"]["content"] or ""
                except (KeyError, IndexError, ValueError):
                    raise LLMError("Unexpected response shape from LLM endpoint")
            last_error = f"HTTP {r.status_code}"
            if r.status_code not in RETRYABLE_STATUS:
                raise LLMError(last_error)  # 401/403/400: retrying won't help
        logger.warning("LLM call failed (%s), attempt %d/%d", last_error, attempt, MAX_ATTEMPTS)
        if attempt < MAX_ATTEMPTS:
            time.sleep(2**attempt)
    raise LLMError(f"LLM failed after {MAX_ATTEMPTS} attempts: {last_error}")