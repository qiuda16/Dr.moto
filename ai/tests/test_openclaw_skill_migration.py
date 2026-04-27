from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.skills import SkillRegistry


def test_migrated_openclaw_skills_load_and_match():
    registry = SkillRegistry(ROOT / "data" / "skills")
    skills = {skill.skill_id: skill for skill in registry.list_skills(force_reload=True)}

    for skill_id in [
        "memory-tiering",
        "automation-workflows",
        "cron-mastery",
        "obsidian",
        "agent-browser",
    ]:
        assert skill_id in skills, skill_id
        assert skills[skill_id].system_prompt.strip(), skill_id

    matched_memory = registry.match_skills("帮我记住这辆车的保养里程和上次工单", query_domains=["customer"])
    assert matched_memory and matched_memory[0].skill_id == "memory-tiering"

    matched_workflow = registry.match_skills("把维修手册入库流程串起来，确认后再写库", query_domains=["project_system"])
    assert any(item.skill_id == "automation-workflows" for item in matched_workflow)

    matched_cron = registry.match_skills("每天凌晨自动检查未完成工单", query_domains=["project_system"])
    assert any(item.skill_id == "cron-mastery" for item in matched_cron)

    matched_obsidian = registry.match_skills("把这份维修手册整理成知识笔记", query_domains=["knowledge"])
    assert any(item.skill_id == "obsidian" for item in matched_obsidian)

    matched_browser = registry.match_skills("对这个前端流程做一次冒烟测试", query_domains=["project_system"])
    assert any(item.skill_id == "agent-browser" for item in matched_browser)
