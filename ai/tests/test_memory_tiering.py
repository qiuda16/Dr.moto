from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import memory


def _use_temp_memory_store(tmp_path: Path, monkeypatch) -> None:
    memory_root = tmp_path / "memory"
    monkeypatch.setattr(memory, "MEMORY_ROOT", memory_root)
    monkeypatch.setattr(memory, "SESSION_MEMORY_PATH", memory_root / "session_memory.json")
    monkeypatch.setattr(memory, "MEMORY_BACKEND", "file")


def test_memory_tiers_include_hot_warm_cold_and_working_events(tmp_path: Path, monkeypatch):
    _use_temp_memory_store(tmp_path, monkeypatch)
    user_id = "u-tier-1"

    memory.remember_working_event(
        user_id,
        "manual_ingest_pipeline",
        status="ok",
        payload={"job_id": 51, "model_id": 2237},
    )

    rounds = memory.MEMORY_KEEP_RECENT_TURNS + 3
    for index in range(rounds):
        memory.remember_session_turn(
            user_id,
            f"第{index}轮 测试编号 ZX-{1000 + index}",
            "工单 123e4567-e89b-12d3-a456-426614174000，车牌 苏A12345",
            business_context={"matched_customer": {"id": 7, "name": "张三"}},
        )

    tiers = memory.recall_memory_tiers(user_id, hot_limit=4, warm_limit=6, cold_limit=10, buffer_limit=5)

    assert 1 <= len(tiers["hot"]) <= 4
    assert tiers["warm"]
    assert tiers["working_buffer"]
    cold_keys = {item.get("key") for item in tiers["cold"] if isinstance(item, dict)}
    assert "customer_id" in cold_keys
    assert "work_order_id" in cold_keys


def test_memory_tiers_backward_compatible_for_legacy_list_payload(tmp_path: Path, monkeypatch):
    _use_temp_memory_store(tmp_path, monkeypatch)
    user_id = "legacy-user"
    memory._save_user_memory(user_id, {"summary": "", "turns": [{"question": "q", "answer": "a"}]})

    tiers = memory.recall_memory_tiers(user_id)

    assert isinstance(tiers, dict)
    assert "hot" in tiers
    assert "warm" in tiers
    assert "cold" in tiers
    assert "working_buffer" in tiers
