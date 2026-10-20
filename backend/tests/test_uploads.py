import pytest

from app.uploads import MAX_UPLOAD_BYTES, UploadError, validate_upload


def status_of(name, data):
    with pytest.raises(UploadError) as e:
        validate_upload(name, data)
    return e.value.status


def test_accepts_txt():
    assert validate_upload("a.txt", b"hello").mime == "text/plain"


def test_accepts_markdown():
    assert validate_upload("a.MD", "# Titre \u00e9".encode()).ext == ".md"


def test_accepts_pdf_header():
    assert validate_upload("a.pdf", b"%PDF-1.7\n...").mime == "application/pdf"


def test_rejects_unknown_extension():
    assert status_of("run.exe", b"hello") == 415


def test_rejects_fake_pdf():
    assert status_of("x.pdf", b"just text") == 415


def test_rejects_binary_text():
    assert status_of("a.txt", b"abc\x00def") == 415


def test_rejects_invalid_utf8():
    assert status_of("a.txt", b"\xff\xfe\xfa") == 415


def test_rejects_empty():
    assert status_of("a.txt", b"") == 400


def test_rejects_too_large():
    assert status_of("a.txt", b"a" * (MAX_UPLOAD_BYTES + 1)) == 413


def test_filename_is_sanitized():
    assert validate_upload("../../etc/passwd.txt", b"x").filename == "passwd.txt"
    assert validate_upload("C:\\Users\\me\\notes.md", b"x").filename == "notes.md"
    long = validate_upload("x" * 300 + ".txt", b"x").filename
    assert len(long) == 255 and long.endswith(".txt")