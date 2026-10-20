import getpass

import httpx

from app.config import get_settings

s = get_settings()
BASE = s.supabase_url.rstrip("/")
REST = f"{BASE}/rest/v1"
KEY = s.supabase_publishable_key
VEC = "[" + ",".join(["1"] + ["0"] * 383) + "]"  # a 384-dimension test vector
results = []


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS" if ok else "FAIL"), name)


def login(label: str):
    email = input(f"{label} email: ")
    password = getpass.getpass(f"{label} password: ")
    r = httpx.post(
        f"{BASE}/auth/v1/token", params={"grant_type": "password"},
        headers={"apikey": KEY}, json={"email": email, "password": password}, timeout=15,
    )
    if r.status_code != 200:
        raise SystemExit(f"{label} login failed ({r.status_code})")
    body = r.json()
    return body["access_token"], body["user"]["id"]


def hdr(token=None, **extra):
    h = {"apikey": KEY, "Content-Type": "application/json", **extra}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def get(path, token=None, **params):
    return httpx.get(f"{REST}/{path}", headers=hdr(token), params=params, timeout=15)


def post(path, body, token=None):
    return httpx.post(f"{REST}/{path}", headers=hdr(token, Prefer="return=representation"), json=body, timeout=15)


def rows(r) -> list:
    return r.json() if r.status_code == 200 and isinstance(r.json(), list) else []


a_token, a_id = login("User A")
b_token, b_id = login("User B")
if a_id == b_id:
    raise SystemExit("User A and User B must be different users.")

doc_id = None
try:
    doc = {"filename": "rls-test.txt", "storage_path": f"{a_id}/rls-test.txt",
           "mime_type": "text/plain", "size_bytes": 10}
    r = post("documents", doc, a_token)
    check("A can insert a document", r.status_code == 201)
    if r.status_code != 201:
        print(r.text[:300])
        raise SystemExit("Cannot continue: check the SQL ran and the grants exist.")
    doc_id = r.json()[0]["id"]

    r = post("document_chunks", {"document_id": doc_id, "chunk_index": 0,
                                 "content": "test chunk", "embedding": VEC}, a_token)
    check("A can insert a chunk with a 384-d embedding", r.status_code == 201)

    check("A can read their own document", any(d["id"] == doc_id for d in rows(get("documents", a_token))))
    check("B cannot see A's document", not any(d["id"] == doc_id for d in rows(get("documents", b_token))))
    check("Anonymous cannot see A's document", not any(d["id"] == doc_id for d in rows(get("documents"))))

    r = httpx.patch(f"{REST}/documents", headers=hdr(b_token, Prefer="return=representation"),
                    params={"id": f"eq.{doc_id}"}, json={"filename": "hacked"}, timeout=15)
    check("B cannot update A's document", rows(r) == [])
    r = httpx.delete(f"{REST}/documents", headers=hdr(b_token, Prefer="return=representation"),
                     params={"id": f"eq.{doc_id}"}, timeout=15)
    check("B cannot delete A's document", rows(r) == [])

    r = post("documents", {**doc, "user_id": a_id, "storage_path": f"{a_id}/spoof.txt",
                           "filename": "rls-test-spoof.txt"}, b_token)
    check("B cannot insert a row owned by A", r.status_code >= 400)
    r = post("document_chunks", {"document_id": doc_id, "chunk_index": 1,
                                 "content": "injected", "embedding": VEC}, b_token)
    check("B cannot attach a chunk to A's document", r.status_code >= 400)
    r = post("documents", {**doc, "storage_path": "someone-else/x.txt",
                           "filename": "rls-test-badpath.txt"}, a_token)
    check("A cannot use a storage path outside their own folder", r.status_code >= 400)

    q = {"query_embedding": VEC, "match_count": 5}
    r = post("rpc/match_document_chunks", q, a_token)
    check("A's similarity search finds A's chunk", len(rows(r)) == 1)
    r = post("rpc/match_document_chunks", q, b_token)
    check("B's similarity search returns nothing of A's", rows(r) == [] and r.status_code == 200)
finally:
    httpx.delete(f"{REST}/documents", headers=hdr(a_token), params={"filename": "like.rls-test*"}, timeout=15)

print(f"\n{sum(results)}/{len(results)} checks passed")