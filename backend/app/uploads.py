import os
import re
from dataclasses import dataclass

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # must match the database and bucket limits
ALLOWED = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class UploadError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    ext: str
    mime: str
    size: int


def clean_filename(name: str) -> str:
    base = os.path.basename(name.replace("\\", "/"))
    return _CONTROL.sub("", base).strip()


def validate_upload(filename: str, data: bytes) -> ValidatedUpload:
    name = clean_filename(filename)
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise UploadError(415, "Only .pdf, .txt and .md files are supported.")
    if len(data) == 0:
        raise UploadError(400, "The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError(413, "File is too large (10 MB maximum).")
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise UploadError(415, "File content is not a valid PDF.")
    else:
        if b"\x00" in data:
            raise UploadError(415, "File content is not text.")
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise UploadError(415, "Text files must be UTF-8 encoded.")
    if len(name) > 255:
        name = name[: 255 - len(ext)] + ext
    return ValidatedUpload(name, ext, ALLOWED[ext], len(data))