import pytest

from app import ingest
from app.ingest import IngestError, chunk_text, extract_text, normalize_text


def make_pdf(pages: list[str]) -> bytes:
    n = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, text in enumerate(pages):
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {5 + 2 * i} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objects.append(page.encode())
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    out, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def test_normalize_text():
    assert normalize_text("a\r\nb\t\t c\x00d\n\n\n\ne  ") == "a\nb cd\n\ne"


def test_extract_txt():
    assert extract_text(b"Hello   world", ".txt").text == "Hello world"


def test_extract_markdown_strips_bom():
    assert extract_text(b"\xef\xbb\xbfhello", ".md").text == "hello"


def test_extract_pdf_text():
    r = extract_text(make_pdf(["Alpha page", "Beta page"]), ".pdf")
    assert "Alpha page" in r.text and "Beta page" in r.text and not r.truncated


def test_pdf_page_cap():
    r = extract_text(make_pdf([f"Page {i}" for i in range(ingest.MAX_PAGES + 5)]), ".pdf")
    assert r.truncated and "Page 0" in r.text and f"Page {ingest.MAX_PAGES}" not in r.text


def test_garbage_pdf_is_rejected():
    with pytest.raises(IngestError):
        extract_text(b"%PDF-1.4 this is not really a pdf", ".pdf")


def test_empty_pdf_is_rejected():
    with pytest.raises(IngestError):
        extract_text(make_pdf([""]), ".pdf")


def test_text_char_cap():
    r = extract_text(("word " * 60000).encode(), ".txt")
    assert r.truncated and len(r.text) == ingest.MAX_TEXT_CHARS


def test_single_short_chunk():
    assert chunk_text("hello world") == (["hello world"], False)


def test_chunks_never_split_words_and_cover_everything():
    tokens = [f"w{i}" for i in range(600)]
    chunks, truncated = chunk_text(" ".join(tokens), size=300, overlap=50)
    seen = set()
    for c in chunks:
        assert len(c) <= 300
        seen.update(c.split())
    assert not truncated and seen == set(tokens)


def test_prefers_paragraph_boundary():
    para = ("word " * 140).strip()  # 699 characters
    chunks, _ = chunk_text(para + "\n\n" + para)
    assert chunks[0] == para


def test_max_chunks_marks_truncated():
    chunks, truncated = chunk_text("word " * 10000, max_chunks=5)
    assert len(chunks) == 5 and truncated


def test_unbroken_text_terminates():
    chunks, truncated = chunk_text("a" * 5000)
    assert len(chunks) == 5 and all(len(c) <= 1000 for c in chunks) and not truncated


def test_low_text_pdf_is_flagged():
    assert extract_text(make_pdf(["Hi there"]), ".pdf").low_text


def test_normal_pdf_is_not_flagged():
    assert not extract_text(make_pdf(["x " * 300]), ".pdf").low_text