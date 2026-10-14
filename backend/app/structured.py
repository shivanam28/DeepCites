import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm import LLMError, complete

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
MAX_PARSE_ATTEMPTS = 2


def _extract_json(text: str) -> str:
    """Models often wrap JSON in prose or code fences; take first '{' to last '}'."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return text[start : end + 1]


def complete_structured(messages: list[dict], schema: type[T], *, max_tokens: int = 800) -> T:
    msgs = list(messages)
    last_error = "unknown"
    for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
        raw = complete(msgs, max_tokens=max_tokens)
        try:
            return schema.model_validate_json(_extract_json(raw))
        except (ValueError, ValidationError) as exc:
            last_error = type(exc).__name__
            logger.warning("Invalid structured output (%s), attempt %d", last_error, attempt)
            msgs = msgs + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": "That was not valid JSON matching the required format. "
                    "Reply again with ONLY the JSON object.",
                },
            ]
    raise LLMError(f"No valid structured output after {MAX_PARSE_ATTEMPTS} attempts: {last_error}")