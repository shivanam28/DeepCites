import getpass
import time

import httpx

from app.config import get_settings

s = get_settings()
BASE = "http://localhost:8000"
BODY = {"question": "Is intermittent fasting effective?"}

print("no token:", httpx.post(f"{BASE}/research", json=BODY).status_code)
print(
    "bad token:",
    httpx.post(f"{BASE}/research", json=BODY, headers={"Authorization": "Bearer not-a-real-token"}).status_code,
)

email = input("Test user email: ")
password = getpass.getpass("Password: ")
login = httpx.post(
    f"{s.supabase_url}/auth/v1/token",
    params={"grant_type": "password"},
    headers={"apikey": s.supabase_publishable_key},
    json={"email": email, "password": password},
    timeout=15.0,
)
print("login:", login.status_code)
if login.status_code != 200:
    raise SystemExit("Login failed. Check the user, password and keys.")
token = login.json()["access_token"]

start = time.monotonic()
with httpx.stream(
    "POST", f"{BASE}/research", json=BODY,
    headers={"Authorization": f"Bearer {token}"}, timeout=180.0,
) as r:
    print("with token:", r.status_code)
    for line in r.iter_lines():
        if line.startswith("event:"):
            print(f"[{time.monotonic() - start:5.1f}s] {line}")