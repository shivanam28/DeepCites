import time

import httpx

start = time.monotonic()
with httpx.stream(
    "POST",
    "http://localhost:8000/research",
    json={"question": "Is intermittent fasting effective?"},
    timeout=180.0,
) as r:
    print("STATUS:", r.status_code)
    for line in r.iter_lines():
        if line:
            print(f"[{time.monotonic() - start:5.1f}s] {line[:200]}")