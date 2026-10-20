import io
import logging
import re
from dataclasses import dataclass

from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_PAGES = 100
MAX_TEXT_CHARS = 200_000
CHUNK_SIZE = 1000      # characters, roughly 200 to 250 tokens
CHUNK_OVERLAP = 150
MAX_CHUNKS = 250       # 200,000 / (1000 - 150) is about 236, so the text cap fits under this
LOW_TEXT_CHARS_PER_PAGE = 100

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # keeps tab and newline


class IngestError(Exception):
    pass


@dataclass(frozen=True)
class ExtractedText:
    text: str
    truncated: bool
    low_text: bool = False  # a PDF with very little text per page: likely scanned or image-based


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = text.replace("\t", " ")
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(data: bytes) -> tuple[str, bool, int]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IngestError("Encrypted PDFs are not supported.")
        parts, total, truncated = [], 0, False
        for i, page in enumerate(reader.pages):
            if i >= MAX_PAGES:
                truncated = True
                break
            page_text = page.extract_text() or ""
            parts.append(page_text)
            total += len(page_text)
            if total >= MAX_TEXT_CHARS:
                truncated = True
                break
        return "\n\n".join(parts), truncated, len(parts)  # same indentation as "for"
    except IngestError:
        raise
    except Exception as exc:  # parsers of untrusted files can fail in many ways
        logger.warning("PDF parsing failed: %s", type(exc).__name__)
        raise IngestError("Could not read this PDF.") from None

def extract_text(data: bytes, ext: str) -> ExtractedText:
    pages = None
    if ext == ".pdf":
        raw, truncated, pages = _extract_pdf(data)
    elif ext in (".txt", ".md"):
        raw, truncated = data.decode("utf-8-sig", errors="replace"), False
    else:
        raise IngestError("Unsupported file type.")

    text = normalize_text(raw)
    if len(text) > MAX_TEXT_CHARS:
        text, truncated = text[:MAX_TEXT_CHARS], True
    if not text:
        raise IngestError("No extractable text found (scanned PDFs are not supported).")
    low_text = pages is not None and len(text) < LOW_TEXT_CHARS_PER_PAGE * pages
    return ExtractedText(text=text, truncated=truncated, low_text=low_text)


def _best_cut(text: str, min_cut: int, end: int) -> int:
    """Prefer a paragraph break, then a line break, then a sentence end, then a space."""
    for sep in ("\n\n", "\n", ". ", " "):
        i = text.rfind(sep, min_cut, end)
        if i != -1:
            return i + len(sep)
    return end


def chunk_text(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP, max_chunks: int = MAX_CHUNKS
) -> tuple[list[str], bool]:
    """Return (chunks, truncated). truncated is True if max_chunks stopped us early."""
    chunks: list[str] = []
    n, start = len(text), 0
    while start < n:
        if len(chunks) >= max_chunks:
            return chunks, True
        end = min(start + size, n)
        cut = n if end == n else _best_cut(text, start + int(size * 0.6), end)
        piece = text[start:cut].strip()
        if piece:
            chunks.append(piece)
        if cut >= n:
            break
        nxt = cut - overlap
        while nxt < cut and not text[nxt].isspace():  # begin the next chunk on a word boundary
            nxt += 1
        start = max(nxt, start + 1)
    return chunks, False