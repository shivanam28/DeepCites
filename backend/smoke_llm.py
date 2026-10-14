import time

from app.llm import complete

start = time.monotonic()
reply = complete(
    [{"role": "user", "content": "Reply with exactly one word: pong"}],
    max_tokens=300,
)
print("REPLY:", repr(reply))
print(f"LATENCY: {time.monotonic() - start:.1f}s")