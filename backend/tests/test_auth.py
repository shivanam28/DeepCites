import httpx
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.auth import AuthUser, get_current_user
from app.config import Settings

app = FastAPI()


@app.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    return {"id": user.id}


client = TestClient(app)
SETTINGS = Settings(
    tavily_api_key="x", llm_api_key="y",
    supabase_url="https://p.supabase.co", supabase_publishable_key="pk",
    _env_file=None,
)


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body


def patch_auth_server(monkeypatch, response=None, error=None):
    seen = {}

    def fake_get(url, headers, timeout):
        seen.update(url=url, headers=headers)
        if error:
            raise error
        return response

    monkeypatch.setattr(auth, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(auth.httpx, "get", fake_get)
    return seen


def test_missing_token_is_401():
    assert client.get("/me").status_code == 401


def test_non_bearer_scheme_is_401():
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_user_id_comes_from_auth_server_not_from_client(monkeypatch):
    seen = patch_auth_server(monkeypatch, FakeResp(200, {"id": "user-123", "email": "a@b.c"}))
    r = client.get("/me", headers={"Authorization": "Bearer tok", "X-User-Id": "attacker"})
    assert r.json() == {"id": "user-123"}
    assert seen["url"] == "https://p.supabase.co/auth/v1/user"
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert seen["headers"]["apikey"] == "pk"


def test_rejected_token_is_401(monkeypatch):
    patch_auth_server(monkeypatch, FakeResp(401))
    assert client.get("/me", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_auth_server_error_is_503(monkeypatch):
    patch_auth_server(monkeypatch, FakeResp(500))
    assert client.get("/me", headers={"Authorization": "Bearer tok"}).status_code == 503


def test_auth_server_unreachable_is_503(monkeypatch):
    patch_auth_server(monkeypatch, error=httpx.ConnectError("down"))
    assert client.get("/me", headers={"Authorization": "Bearer tok"}).status_code == 503