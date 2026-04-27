from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.agent_runtime import SlimOpenClawRuntime


def test_agent_runtime_loads_workspace_docs(tmp_path: Path):
    workspace = tmp_path / "agent_workspace"
    state = tmp_path / "agent_state"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "AGENTS.md").write_text("agent role", encoding="utf-8")
    (workspace / "TOOLS.md").write_text("tool list", encoding="utf-8")

    runtime = SlimOpenClawRuntime(workspace, state)
    docs = runtime.load_prompt_docs()

    assert docs["AGENTS.md"] == "agent role"
    assert docs["TOOLS.md"] == "tool list"


def test_agent_runtime_task_registry_roundtrip(tmp_path: Path):
    runtime = SlimOpenClawRuntime(tmp_path / "agent_workspace", tmp_path / "agent_state")
    task = runtime.upsert_task(
        "ocr-followup",
        "Continue OCR manual import",
        status="pending",
        source="ocr",
        payload={"job_id": 51},
    )

    assert task["id"] == "ocr-followup"
    items = runtime.list_tasks()
    assert len(items) == 1
    assert items[0]["payload"]["job_id"] == 51
