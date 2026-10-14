import logging

from tavily import TavilyClient

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_SNIPPET_CHARS = 1000


def web_search(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """Return [{title, url, snippet}, ...]. Returns [] on any failure."""
    client = TavilyClient(api_key=get_settings().tavily_api_key)
    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=min(max_results, MAX_RESULTS),
        )
    except Exception as exc:
        # Log only the exception class, never the message, which could echo request details.
        logger.warning("Tavily search failed: %s", type(exc).__name__)
        return []

    results = []
    for r in response.get("results", []):
        results.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": (r.get("content") or "")[:MAX_SNIPPET_CHARS],
            }
        )
    return results