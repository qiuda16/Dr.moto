from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.customer_agent import CustomerServiceAgent
from app.routers.customer_agent import build_customer_agent_router


def test_customer_agent_router_tools_and_plan(tmp_path: Path):
    agent = CustomerServiceAgent(tmp_path / "agent_workspace")
    app = FastAPI()
    app.include_router(build_customer_agent_router(agent))
    client = TestClient(app)

    tools_resp = client.get("/customer-agent/tools")
    assert tools_resp.status_code == 200
    assert tools_resp.json()["count"] >= 8

    plan_resp = client.post(
        "/customer-agent/plan",
        json={"message": "create quote draft", "context": {"vehicle_id": 1, "work_order_id": "wo-1", "service_items": ["oil"]}},
    )
    assert plan_resp.status_code == 200
    plan = plan_resp.json()["plan"]
    assert plan["intent"] == "create_quote_draft"
    assert plan["requires_confirmation"] is True


def test_customer_agent_router_can_bootstrap_openclaw(tmp_path: Path):
    openclaw_workspace = tmp_path / "openclaw_workspace"
    openclaw_workspace.mkdir(parents=True, exist_ok=True)
    (openclaw_workspace / "AGENTS.md").write_text("openclaw agents", encoding="utf-8")
    (openclaw_workspace / "SOUL.md").write_text("openclaw soul", encoding="utf-8")

    agent = CustomerServiceAgent(tmp_path / "agent_workspace")
    app = FastAPI()
    app.include_router(build_customer_agent_router(agent))
    client = TestClient(app)

    resp = client.post(
        "/customer-agent/bootstrap-openclaw",
        json={"workspace_root": str(openclaw_workspace)},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["imported"] is True
    assert "AGENTS.md" in result["files"]
