import getpass

import httpx

from app.config import get_settings

s = get_settings()
BASE = "http://localhost:8000"
SB = s.supabase_url.rstrip("/")
KEY = s.supabase_publishable_key
MAX = 10 * 1024 * 1024
results = []


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
    body = r.json()
    return body["access_token"], body["user"]["id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def upload(token, name, data, ctype="application/octet-stream"):
    return httpx.post(f"{BASE}/documents", headers=auth(token),
                      files={"file": (name, data, ctype)}, timeout=60)


def listing(token):
    return httpx.get(f"{BASE}/documents", headers=auth(token), timeout=30).json()


def storage_get(token, path):
    return httpx.get(f"{SB}/storage/v1/object/documents/{path}",
                     headers={"apikey": KEY, **auth(token)}, timeout=30)


a_token, a_id = login("User A")
b_token, b_id = login("User B")
if a_id == b_id:
    raise SystemExit("User A and User B must be different users.")

doc_id = None
try:
    check("Upload without a token is rejected (401)", upload(None, "a.txt", b"hello").status_code == 401)
    check("Unsupported file type is rejected (415)", upload(a_token, "run.exe", b"MZ...").status_code == 415)
    check("Fake PDF is rejected (415)", upload(a_token, "x.pdf", b"just text").status_code == 415)
    check("Empty file is rejected (400)", upload(a_token, "e.txt", b"").status_code == 400)
    check("Oversized file is rejected (413)", upload(a_token, "big.txt", b"a" * (MAX + 1)).status_code == 413)

    r = upload(a_token, "note.txt", b"hello deepcites", "text/plain")
    check("A can upload a text file (201)", r.status_code == 201)
    if r.status_code != 201:
        print(r.text[:300])
        raise SystemExit("Cannot continue: check the server log and the SQL.")
    doc_id = r.json()["id"]
    path = f"{a_id}/{doc_id}.txt"

    check("A sees the document in their list", any(d["id"] == doc_id for d in listing(a_token)))
    check("B does not see it", not any(d["id"] == doc_id for d in listing(b_token)))
    got = storage_get(a_token, path)
    check("A can download their stored file", got.status_code == 200 and got.content == b"hello deepcites")
    check("B cannot download A's file", storage_get(b_token, path).status_code != 200)
    r = httpx.delete(f"{BASE}/documents/{doc_id}", headers=auth(b_token), timeout=30)
    check("B cannot delete A's document (404)", r.status_code == 404)
    r = httpx.delete(f"{BASE}/documents/{doc_id}", headers=auth(a_token), timeout=30)
    check("A can delete their document (204)", r.status_code == 204)
    doc_id = None
    check("The file is gone from storage", storage_get(a_token, path).status_code != 200)
finally:
    if doc_id:
        httpx.delete(f"{BASE}/documents/{doc_id}", headers=auth(a_token), timeout=30)

print(f"\n{sum(results)}/{len(results)} checks passed")