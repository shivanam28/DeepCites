from app import llm
from app.config import Settings


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 2},
        }


def test_extra_body_is_merged_but_cannot_override_core_fields(monkeypatch):
    settings = Settings(
        tavily_api_key="x",
        llm_api_key="y",
        llm_extra_body={"chat_template_kwargs": {"enable_thinking": False}, "model": "evil"},
        _env_file=None,
        supabase_url="https://p.supabase.co",
        supabase_publishable_key="pk",
    )
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(json)
        return FakeResponse()

    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setattr(llm, "_throttle", lambda rpm: None)

    assert llm.complete([{"role": "user", "content": "x"}]) == "hi"
    assert sent["chat_template_kwargs"] == {"enable_thinking": False}
    assert sent["model"] == settings.llm_model