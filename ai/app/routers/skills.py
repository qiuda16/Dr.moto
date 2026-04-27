from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.skills import SkillRegistry


class SkillUpsertRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 100
    trigger_keywords: List[str] = Field(default_factory=list)
    trigger_regexes: List[str] = Field(default_factory=list)
    required_query_domains: List[str] = Field(default_factory=list)
    context_keys_any: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    example_queries: List[str] = Field(default_factory=list)
    system_prompt: str = ""
    prompt_file: str = "prompt.md"


class SkillStateRequest(BaseModel):
    enabled: bool


def build_skills_router(registry: SkillRegistry, root_path: Path) -> APIRouter:
    router = APIRouter(prefix="/skills", tags=["Skills"])

    @router.get("")
    async def list_skills(force_reload: bool = False) -> Dict[str, Any]:
        items = [item.to_public_dict() for item in registry.list_skills(force_reload=force_reload)]
        return {"items": items, "count": len(items), "root_path": str(root_path)}

    @router.post("/reload")
    async def reload_skills() -> Dict[str, Any]:
        loaded = registry.reload()
        return {"reloaded": len(loaded), "items": [item.to_public_dict() for item in registry.list_skills()]}

    @router.post("")
    async def install_skill(payload: SkillUpsertRequest) -> Dict[str, Any]:
        skill = registry.upsert_skill(payload.dict())
        return {"installed": True, "skill": skill.to_public_dict()}

    @router.patch("/{skill_id}")
    async def update_skill_state(skill_id: str, payload: SkillStateRequest) -> Dict[str, Any]:
        try:
            skill = registry.set_enabled(skill_id, payload.enabled)
        except KeyError:
            raise HTTPException(status_code=404, detail="skill not found")
        return {"updated": True, "skill": skill.to_public_dict()}

    @router.delete("/{skill_id}")
    async def delete_skill(skill_id: str) -> Dict[str, Any]:
        try:
            registry.delete_skill(skill_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="skill not found")
        return {"deleted": True, "id": skill_id}

    return router
