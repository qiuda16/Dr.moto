from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import openclaw_models


def test_resolve_openclaw_primary_target_from_json(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "openclaw.json"
    models_path = tmp_path / "models.json"
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {
                        "model": {"primary": "minimax/MiniMax-M2.7"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    models_path.write_text(
        json.dumps(
            {
                "providers": {
                    "minimax": {
                        "baseUrl": "https://api.minimaxi.com/anthropic/v1",
                        "api": "anthropic-messages",
                        "authHeader": True,
                        "apiKey": "k",
                        "models": [{"id": "MiniMax-M2.7"}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(openclaw_models, "OPENCLAW_CONFIG_JSON", str(config_path))
    monkeypatch.setattr(openclaw_models, "OPENCLAW_MODELS_JSON", str(models_path))
    openclaw_models.load_openclaw_model_config.cache_clear()

    target = openclaw_models.resolve_openclaw_primary_target()

    assert target["provider_key"] == "minimax"
    assert target["model_id"] == "MiniMax-M2.7"
    assert target["api"] == "anthropic-messages"
    assert target["base_url"] == "https://api.minimaxi.com/anthropic/v1"


def test_call_openclaw_text_chat_parses_anthropic_response(monkeypatch):
    monkeypatch.setattr(
        openclaw_models,
        "resolve_openclaw_primary_target",
        lambda: {
            "provider_key": "minimax",
            "model_id": "MiniMax-M2.7",
            "base_url": "https://api.minimaxi.com/anthropic/v1",
            "api": "anthropic-messages",
            "api_key": "test-key",
            "auth_header": True,
        },
    )

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "ok"}]}

    def _fake_post(url, headers, json, timeout):  # noqa: A002
        assert url.endswith("/messages")
        assert headers.get("x-api-key") == "test-key"
        assert json.get("model") == "MiniMax-M2.7"
        return _Resp()

    monkeypatch.setattr(openclaw_models.requests, "post", _fake_post)

    text = openclaw_models.call_openclaw_text_chat(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    )

    assert text == "ok"
