from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.agent_runtime import SlimOpenClawRuntime


class AgentTaskRequest(BaseModel):
    id: str
    title: str
    status: str = "pending"
    source: str = "manual"
    payload: Dict[str, Any] = {}


def build_agent_runtime_router(runtime: SlimOpenClawRuntime) -> APIRouter:
    router = APIRouter(prefix="/agent-runtime", tags=["Agent Runtime"])

    @router.get("")
    async def get_agent_runtime_summary() -> Dict[str, Any]:
        return runtime.workspace_summary()

    @router.get("/tasks")
    async def list_agent_tasks(status: Optional[str] = None) -> Dict[str, Any]:
        items = runtime.list_tasks()
        if status:
            items = [item for item in items if str(item.get("status") or "") == status]
        return {"items": items, "count": len(items)}

    @router.post("/tasks")
    async def upsert_agent_task(payload: AgentTaskRequest) -> Dict[str, Any]:
        try:
            item = runtime.upsert_task(
                payload.id,
                payload.title,
                status=payload.status,
                source=payload.source,
                payload=payload.payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"task": item}

    return router
