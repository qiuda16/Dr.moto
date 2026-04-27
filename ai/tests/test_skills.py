from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.skills import SkillRegistry


def test_skill_registry_upsert_and_match(tmp_path: Path):
    registry = SkillRegistry(tmp_path / "skills")
    installed = registry.upsert_skill(
        {
            "id": "service_writer",
            "name": "Service Writer",
            "description": "Help with intake and estimate wording",
            "enabled": True,
            "priority": 20,
            "trigger_keywords": ["报价", "接待"],
            "required_query_domains": ["work_order"],
            "context_keys_any": ["matched_work_order"],
            "suggested_actions": ["继续让我整理报价话术"],
            "system_prompt": "你当前启用了接待报价技能。",
        }
    )

    assert installed.skill_id == "service_writer"
    assert installed.system_prompt == "你当前启用了接待报价技能。"

    matched = registry.match_skills(
        "帮我整理这个工单的报价话术",
        business_context={"matched_work_order": {"id": "wo-1"}},
        query_domains=["work_order"],
    )
    assert [item.skill_id for item in matched] == ["service_writer"]


def test_skill_registry_respects_disabled_flag(tmp_path: Path):
    registry = SkillRegistry(tmp_path / "skills")
    registry.upsert_skill(
        {
            "id": "disabled_skill",
            "name": "Disabled",
            "enabled": False,
            "trigger_keywords": ["机油"],
            "system_prompt": "disabled",
        }
    )

    matched = registry.match_skills("这台车机油用什么规格", query_domains=["knowledge"])
    assert matched == []
