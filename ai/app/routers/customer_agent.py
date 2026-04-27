from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from ..core.customer_agent import CustomerServiceAgent


class AgentPlanRequest(BaseModel):
    message: str
    context: Dict[str, Any] = {}


class OpenClawImportRequest(BaseModel):
    workspace_root: str = ""


def build_customer_agent_router(agent: CustomerServiceAgent) -> APIRouter:
    router = APIRouter(prefix="/customer-agent", tags=["Customer Agent"])

    @router.get("")
    async def customer_agent_summary() -> Dict[str, Any]:
        return {
            "agent_id": "drmoto_customer_service_agent",
            "tools_count": len(agent.list_tools()),
            "openclaw_reference": agent.openclaw_reference(),
        }

    @router.get("/tools")
    async def customer_agent_tools() -> Dict[str, Any]:
        items = agent.list_tools()
        return {"items": items, "count": len(items)}

    @router.post("/plan")
    async def customer_agent_plan(payload: AgentPlanRequest) -> Dict[str, Any]:
        plan = agent.plan(payload.message, payload.context)
        return {"plan": plan}

    @router.post("/bootstrap-openclaw")
    async def bootstrap_openclaw(payload: OpenClawImportRequest) -> Dict[str, Any]:
        source = Path(payload.workspace_root).expanduser() if payload.workspace_root else None
        result = agent.bootstrap_from_openclaw(source)
        return {"result": result}

    return router
