from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip().lower())
    normalized = normalized.strip("-_")
    return normalized or "skill"


@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 100
    trigger_keywords: List[str] = field(default_factory=list)
    trigger_regexes: List[str] = field(default_factory=list)
    required_query_domains: List[str] = field(default_factory=list)
    context_keys_any: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    example_queries: List[str] = field(default_factory=list)
    system_prompt: str = ""
    source_dir: str = ""
    prompt_file: str = "prompt.md"
    updated_at: float = 0.0

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "trigger_keywords": list(self.trigger_keywords),
            "trigger_regexes": list(self.trigger_regexes),
            "required_query_domains": list(self.required_query_domains),
            "context_keys_any": list(self.context_keys_any),
            "suggested_actions": list(self.suggested_actions),
            "example_queries": list(self.example_queries),
            "source_dir": self.source_dir,
            "prompt_file": self.prompt_file,
            "prompt_chars": len(self.system_prompt or ""),
            "updated_at": self.updated_at,
        }


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    return payload if isinstance(payload, dict) else {}


def _normalize_list(payload: Dict[str, Any], key: str) -> List[str]:
    value = payload.get(key) or []
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _load_skill_from_dir(skill_dir: Path) -> Optional[SkillDefinition]:
    manifest_path = skill_dir / "skill.json"
    if not manifest_path.exists():
        return None
    payload = _read_json(manifest_path)
    skill_id = _slugify(str(payload.get("id") or skill_dir.name))
    prompt_file = str(payload.get("prompt_file") or "prompt.md").strip() or "prompt.md"
    prompt_path = skill_dir / prompt_file
    system_prompt = str(payload.get("system_prompt") or "").strip()
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    updated_at = manifest_path.stat().st_mtime
    if prompt_path.exists():
        updated_at = max(updated_at, prompt_path.stat().st_mtime)
    return SkillDefinition(
        skill_id=skill_id,
        name=str(payload.get("name") or skill_id).strip(),
        description=str(payload.get("description") or "").strip(),
        enabled=bool(payload.get("enabled", True)),
        priority=int(payload.get("priority") or 100),
        trigger_keywords=_normalize_list(payload, "trigger_keywords"),
        trigger_regexes=_normalize_list(payload, "trigger_regexes"),
        required_query_domains=_normalize_list(payload, "required_query_domains"),
        context_keys_any=_normalize_list(payload, "context_keys_any"),
        suggested_actions=_normalize_list(payload, "suggested_actions"),
        example_queries=_normalize_list(payload, "example_queries"),
        system_prompt=system_prompt,
        source_dir=str(skill_dir),
        prompt_file=prompt_file,
        updated_at=updated_at,
    )


class SkillRegistry:
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self._lock = threading.Lock()
        self._skills: Dict[str, SkillDefinition] = {}

    def reload(self) -> Dict[str, SkillDefinition]:
        with self._lock:
            self.root_path.mkdir(parents=True, exist_ok=True)
            loaded: Dict[str, SkillDefinition] = {}
            for skill_dir in sorted(self.root_path.iterdir()):
                if not skill_dir.is_dir():
                    continue
                try:
                    skill = _load_skill_from_dir(skill_dir)
                except Exception:
                    continue
                if skill:
                    loaded[skill.skill_id] = skill
            self._skills = loaded
            return dict(self._skills)

    def list_skills(self, force_reload: bool = False) -> List[SkillDefinition]:
        if force_reload or not self._skills:
            self.reload()
        return sorted(self._skills.values(), key=lambda item: (item.priority, item.name.lower()))

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        if not self._skills:
            self.reload()
        return self._skills.get(_slugify(skill_id))

    def upsert_skill(self, payload: Dict[str, Any]) -> SkillDefinition:
        skill_id = _slugify(str(payload.get("id") or payload.get("name") or "skill"))
        skill_dir = self.root_path / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = str(payload.get("prompt_file") or "prompt.md").strip() or "prompt.md"
        prompt_text = str(payload.get("system_prompt") or "").strip()
        if prompt_text:
            (skill_dir / prompt_file).write_text(prompt_text + "\n", encoding="utf-8")

        manifest = {
            "id": skill_id,
            "name": str(payload.get("name") or skill_id).strip(),
            "description": str(payload.get("description") or "").strip(),
            "enabled": bool(payload.get("enabled", True)),
            "priority": int(payload.get("priority") or 100),
            "trigger_keywords": _normalize_list(payload, "trigger_keywords"),
            "trigger_regexes": _normalize_list(payload, "trigger_regexes"),
            "required_query_domains": _normalize_list(payload, "required_query_domains"),
            "context_keys_any": _normalize_list(payload, "context_keys_any"),
            "suggested_actions": _normalize_list(payload, "suggested_actions"),
            "example_queries": _normalize_list(payload, "example_queries"),
            "prompt_file": prompt_file,
        }
        (skill_dir / "skill.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.reload()
        skill = self.get_skill(skill_id)
        if not skill:
            raise RuntimeError(f"failed to load installed skill: {skill_id}")
        return skill

    def set_enabled(self, skill_id: str, enabled: bool) -> SkillDefinition:
        current = self.get_skill(skill_id)
        if not current:
            raise KeyError(skill_id)
        payload = current.to_public_dict()
        payload["enabled"] = bool(enabled)
        payload["system_prompt"] = current.system_prompt
        return self.upsert_skill(payload)

    def delete_skill(self, skill_id: str) -> None:
        current = self.get_skill(skill_id)
        if not current:
            raise KeyError(skill_id)
        skill_dir = Path(current.source_dir)
        if skill_dir.exists():
            for child in sorted(skill_dir.glob("**/*"), reverse=True):
                if child.is_file():
                    child.unlink()
            for child in sorted(skill_dir.glob("**/*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            skill_dir.rmdir()
        self.reload()

    def match_skills(
        self,
        message: str,
        business_context: Optional[Dict[str, Any]] = None,
        query_domains: Optional[List[str]] = None,
        limit: int = 3,
    ) -> List[SkillDefinition]:
        skills = self.list_skills()
        lowered = str(message or "").lower()
        context = business_context or {}
        domains = set(str(item).strip() for item in (query_domains or []) if str(item).strip())
        ranked: List[tuple[int, SkillDefinition]] = []
        for skill in skills:
            if not skill.enabled:
                continue
            score = 0
            for keyword in skill.trigger_keywords:
                if keyword.lower() in lowered:
                    score += 10
            for pattern in skill.trigger_regexes:
                try:
                    if re.search(pattern, message or "", flags=re.IGNORECASE):
                        score += 14
                except re.error:
                    continue
            if skill.required_query_domains:
                overlap = len(domains.intersection(skill.required_query_domains))
                if overlap == 0:
                    continue
                score += overlap * 6
            if skill.context_keys_any:
                if any(context.get(key) for key in skill.context_keys_any):
                    score += 4
            if score > 0:
                ranked.append((score, skill))
        ranked.sort(key=lambda item: (-item[0], item[1].priority, item[1].name.lower()))
        return [skill for _, skill in ranked[: max(1, limit)]]
