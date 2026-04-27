from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import main as ai_main


def _patch_chat_dependencies(monkeypatch):
    monkeypatch.setattr(ai_main.settings, "LLM_PROVIDER", "openclaw")
    monkeypatch.setattr(ai_main.settings, "AI_LLM_FIRST_RESPONSES", True)
    monkeypatch.setattr(ai_main.settings, "AI_RECOVERY_MODE", False)
    monkeypatch.setattr(ai_main.settings, "AI_DEBUG_CONTEXT", True)
    monkeypatch.setattr(ai_main, "_enrich_context", lambda req: {"memory_user_id": req.user_id})
    monkeypatch.setattr(ai_main, "query_kb", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_main, "remember_working_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_main, "remember_session_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_main, "recall_session_memory", lambda *args, **kwargs: [])
    monkeypatch.setattr(ai_main, "recall_session_summary", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        ai_main,
        "recall_memory_tiers",
        lambda *args, **kwargs: {"hot": [], "warm": [], "cold": [], "working_buffer": []},
    )


def test_llm_first_skips_low_info_template(monkeypatch):
    _patch_chat_dependencies(monkeypatch)
    calls = []

    def fake_openclaw(messages):
        calls.append(messages)
        return "模型根据问题先判断：这个请求太泛，需要补一个客户、车牌或工单对象。"

    monkeypatch.setattr(ai_main, "_call_openclaw_chat", fake_openclaw)

    response = TestClient(ai_main.app).post(
        "/chat",
        json={"user_id": "u1", "message": "查一下", "context": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls
    assert payload["response"].startswith("模型根据问题先判断")
    assert not payload["debug"].get("fast_path_used")
    assert payload["debug"]["provider_effective"] == "openclaw"


def test_llm_first_skips_write_guidance_template(monkeypatch):
    _patch_chat_dependencies(monkeypatch)
    calls = []

    def fake_openclaw(messages):
        calls.append(messages)
        return "可以新增客户。我会先收集姓名、手机号和车辆信息，再生成待确认内容。"

    monkeypatch.setattr(ai_main, "_call_openclaw_chat", fake_openclaw)

    response = TestClient(ai_main.app).post(
        "/chat",
        json={"user_id": "u1", "message": "新建客户需要哪些字段", "context": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls
    assert "待确认" in payload["response"]
    assert not payload["debug"].get("write_guidance_fast_path")


def test_llm_first_skips_common_service_template(monkeypatch):
    _patch_chat_dependencies(monkeypatch)
    calls = []

    def fake_openclaw(messages):
        calls.append(messages)
        return "后刹异响先分安全风险和噪音来源：先测制动力，再查刹车片、刹车盘和卡钳回位。"

    monkeypatch.setattr(ai_main, "_call_openclaw_chat", fake_openclaw)

    response = TestClient(ai_main.app).post(
        "/chat",
        json={"user_id": "u1", "message": "后刹异响怎么排查", "context": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls
    assert "后刹异响" in payload["response"]
    assert not payload["debug"].get("common_service_fast_path")
