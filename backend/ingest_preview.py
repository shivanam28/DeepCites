import sys
from pathlib import Path

from app.ingest import IngestError, chunk_text, extract_text

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles choke on some characters

if len(sys.argv) != 2:
    raise SystemExit("usage: python ingest_preview.py <file.pdf|file.txt|file.md>")

path = Path(sys.argv[1])
try:
    result = extract_text(path.read_bytes(), path.suffix.lower())
except IngestError as exc:
    raise SystemExit(f"Could not extract text: {exc}")

chunks, chunks_truncated = chunk_text(result.text)
sizes = [len(c) for c in chunks]
print(f"characters: {len(result.text)}   extraction truncated: {result.truncated}")
print(f"chunks: {len(chunks)}   chunking truncated: {chunks_truncated}")
print(f"chunk size: min {min(sizes)}, max {max(sizes)}")
print("\n--- first chunk ---\n" + chunks[0][:400])
print("\n--- last chunk ---\n" + chunks[-1][:400])