from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.customer_agent import CustomerServiceAgent


def test_customer_agent_plan_for_quote_requires_confirmation(tmp_path: Path):
    workspace = tmp_path / "agent_workspace"
    agent = CustomerServiceAgent(workspace)

    plan = agent.plan(
        "帮我生成这台车的报价草稿",
        {"vehicle_id": 126, "work_order_id": "wo-1", "service_items": ["换机油"]},
    )

    assert plan["intent"] == "create_quote_draft"
    assert plan["requires_confirmation"] is True
    assert plan["risk_level"] == "high"
    assert any(step["tool_id"] == "write_quote_draft" for step in plan["steps"])


def test_customer_agent_plan_for_manual_query_is_read_only(tmp_path: Path):
    workspace = tmp_path / "agent_workspace"
    agent = CustomerServiceAgent(workspace)

    plan = agent.plan("这台车换机油扭矩是多少", {"model_id": 2237, "query": "机油扭矩"})

    assert plan["intent"] == "manual_guidance"
    assert plan["requires_confirmation"] is False
    assert all(step["mode"] == "read" for step in plan["steps"])


def test_customer_agent_can_read_openclaw_reference(tmp_path: Path):
    workspace = tmp_path / "agent_workspace"
    openclaw_workspace = tmp_path / "openclaw_workspace"
    openclaw_workspace.mkdir(parents=True, exist_ok=True)
    (openclaw_workspace / "AGENTS.md").write_text("agent-root", encoding="utf-8")
    (openclaw_workspace / "TOOLS.md").write_text("tool-root", encoding="utf-8")

    agent = CustomerServiceAgent(workspace, openclaw_workspace_root=openclaw_workspace)
    ref = agent.openclaw_reference()

    assert ref["connected"] is True
    assert ref["loaded_docs"]["AGENTS.md"] > 0


def test_customer_agent_manual_ingest_intent_is_high_risk(tmp_path: Path):
    workspace = tmp_path / "agent_workspace"
    agent = CustomerServiceAgent(workspace)

    plan = agent.plan(
        "请把这份维修手册识别并导入",
        {"model_id": 2237, "document_id": 334},
    )

    assert plan["intent"] == "manual_ingest_pipeline"
    assert plan["requires_confirmation"] is True
    assert plan["risk_level"] == "high"
    assert any(step["tool_id"] == "write_manual_ingest_pipeline" for step in plan["steps"])
