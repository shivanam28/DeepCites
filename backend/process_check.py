import getpass
import sys
from pathlib import Path

import httpx

from app.config import get_settings

s = get_settings()
BASE = "http://localhost:8000"
SB = s.supabase_url.rstrip("/")
KEY = s.supabase_publishable_key
results = []
GENERATED = (
    "DeepCites stores document chunks in PostgreSQL with the pgvector extension. "
    "Each chunk is embedded with a small local model and searched by cosine distance. "
) * 30


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS" if ok else "FAIL"), name)


def login(label: str):
    email = input(f"{label} email: ")
    password = getpass.getpass(f"{label} password: ")
    r = httpx.post(f"{SB}/auth/v1/token", params={"grant_type": "password"},
                   headers={"apikey": KEY}, json={"email": email, "password": password}, timeout=15)
    if r.status_code != 200:
        raise SystemExit(f"{label} login failed ({r.status_code})")
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def upload(token, name, data):
    return httpx.post(f"{BASE}/documents", headers=auth(token),
                      files={"file": (name, data, "application/octet-stream")}, timeout=60)


def chunks_of(token, doc_id):
    r = httpx.get(f"{SB}/rest/v1/document_chunks", headers={"apikey": KEY, **auth(token)},
                  params={"document_id": f"eq.{doc_id}", "select": "id"}, timeout=30)
    return r.json() if r.status_code == 200 else None


a_token = login("User A")
b_token = login("User B")
ids = []
try:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        name, data = p.name, p.read_bytes()
    else:
        name, data = "process-test.txt", GENERATED.encode()

    r = upload(a_token, name, data)
    check("A uploads the file (201)", r.status_code == 201)
    if r.status_code != 201:
        print(r.text[:300])
        raise SystemExit("Cannot continue.")
    doc_id = r.json()["id"]
    ids.append(doc_id)

    print("Processing (the first run downloads the embedding model, so this can take a while)...")
    r = httpx.post(f"{BASE}/documents/{doc_id}/process", headers=auth(a_token), timeout=300)
    body = r.json() if r.status_code == 200 else {}
    if r.status_code != 200:
        print(r.status_code, r.text[:300])
    check("Processing finishes with status ready", body.get("status") == "ready")
    print("   chunk_count:", body.get("chunk_count"), "| detail:", body.get("status_detail"))
    check("At least one chunk was created", (body.get("chunk_count") or 0) >= 1)

    listed = {d["id"]: d for d in httpx.get(f"{BASE}/documents", headers=auth(a_token), timeout=30).json()}
    check("The documents list shows status ready", listed.get(doc_id, {}).get("status") == "ready")
    check("A sees exactly that many stored chunks", len(chunks_of(a_token, doc_id) or []) == body.get("chunk_count"))
    check("B cannot see A's chunks", chunks_of(b_token, doc_id) == [])
    r = httpx.post(f"{BASE}/documents/{doc_id}/process", headers=auth(b_token), timeout=60)
    check("B cannot process A's document (404)", r.status_code == 404)

    r = upload(a_token, "blank.txt", b"   \n  \n ")
    if r.status_code == 201:
        blank_id = r.json()["id"]
        ids.append(blank_id)
        body = httpx.post(f"{BASE}/documents/{blank_id}/process", headers=auth(a_token), timeout=60).json()
        check("A blank file fails with a clear reason",
              body.get("status") == "failed" and "No extractable text" in (body.get("status_detail") or ""))
        check("A failed document leaves no chunks", chunks_of(a_token, blank_id) == [])
finally:
    for i in ids:
        httpx.delete(f"{BASE}/documents/{i}", headers=auth(a_token), timeout=30)

print(f"\n{sum(results)}/{len(results)} checks passed")