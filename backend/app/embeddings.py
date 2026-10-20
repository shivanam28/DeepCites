import logging
import threading

from app.config import get_settings

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384  # must match the vector(384) column

_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            from fastembed import TextEmbedding  # imported lazily: slow to import, not needed by most tests

            logger.info("Loading embedding model (the first run downloads it)")
            _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=get_settings().embedding_cache_dir)
    return _model


def _to_list(vector) -> list[float]:
    values = [float(x) for x in vector]
    if len(values) != DIMENSIONS:
        raise RuntimeError(f"Embedding has {len(values)} dimensions, expected {DIMENSIONS}")
    return values


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [_to_list(v) for v in _load().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    return _to_list(next(iter(_load().query_embed(text))))