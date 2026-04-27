from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


RUNTIME_DOC_FILES = ["AGENTS.md", "SOUL.md", "TOOLS.md", "HEARTBEAT.md", "MEMORY.md"]


@dataclass
class AgentTask:
    task_id: str
    title: str
    status: str = "pending"
    source: str = "manual"
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.task_id,
            "title": self.title,
            "status": self.status,
            "source": self.source,
            "payload": dict(self.payload),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SlimOpenClawRuntime:
    def __init__(self, workspace_root: Path, state_root: Path) -> None:
        self.workspace_root = workspace_root
        self.state_root = state_root
        self.tasks_path = self.state_root / "tasks.json"
        self._lock = threading.Lock()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "workspace_prompt_bundle",
                "source": "openclaw/workspace",
                "kept": True,
                "why": "保留 AGENTS/SOUL/TOOLS/HEARTBEAT 这类长期提示骨架，强化 DrMoto agent 身份和行为约束。",
            },
            {
                "key": "skills_runtime",
                "source": "openclaw/skills",
                "kept": True,
                "why": "保留按意图匹配并注入 prompt 的技能层，适合门店场景扩展。",
            },
            {
                "key": "task_registry",
                "source": "openclaw/task-registry",
                "kept": True,
                "why": "保留轻量任务注册能力，用来承接多步工单、AI手册解析、报价跟进。",
            },
            {
                "key": "heartbeat_runtime",
                "source": "openclaw/gateway/heartbeat",
                "kept": True,
                "why": "保留周期巡检和恢复思路，适合店务摘要与异常恢复。",
            },
            {
                "key": "recovery_failover",
                "source": "openclaw/agent/embedded",
                "kept": True,
                "why": "保留 failover / recovery 模式，避免模型或工具异常时直接失能。",
            },
            {
                "key": "tool_policy",
                "source": "openclaw/tool-policy",
                "kept": True,
                "why": "保留能力边界和工具准入概念，适配 BFF/AI解析/KB 的受控调用。",
            },
            {
                "key": "multi_channel_gateway",
                "source": "openclaw/gateway",
                "kept": False,
                "why": "DrMoto 当前只需要应用内 AI 服务，不需要完整多通道消息网关。",
            },
            {
                "key": "plugin_marketplace",
                "source": "openclaw/plugins/clawhub",
                "kept": False,
                "why": "当前先做本地 skill 安装和项目内管理，不接外部市场。",
            },
            {
                "key": "desktop_canvas_browser",
                "source": "openclaw/canvas/browser",
                "kept": False,
                "why": "现阶段门店 AI 不需要桌面控制、Canvas 和浏览器编排。",
            },
            {
                "key": "remote_pairing_and_devices",
                "source": "openclaw/device-pair/phone-control",
                "kept": False,
                "why": "和 DrMoto 当前业务闭环无关，先移除复杂设备层。",
            },
        ]

    def _doc_path(self, name: str) -> Path:
        return self.workspace_root / name

    def load_prompt_docs(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in RUNTIME_DOC_FILES:
            path = self._doc_path(name)
            if path.exists():
                result[name] = path.read_text(encoding="utf-8").strip()
        return result

    def workspace_summary(self) -> Dict[str, Any]:
        docs = self.load_prompt_docs()
        return {
            "workspace_root": str(self.workspace_root),
            "state_root": str(self.state_root),
            "loaded_docs": {name: len(text) for name, text in docs.items()},
            "capabilities": self.list_capabilities(),
        }

    def build_runtime_prompt_block(self, query_domains: List[str], business_context: Dict[str, Any]) -> str:
        docs = self.load_prompt_docs()
        sections: List[str] = []
        role_line = "你运行在 DrMoto 的精简 OpenClaw runtime 中。优先做门店业务可执行动作，不展示通用框架语言。"
        sections.append(role_line)

        domain_focus: List[str] = []
        if "work_order" in query_domains:
            domain_focus.append("当前优先按工单代理思路工作：识别对象、判断节点、给出下一步。")
        if "knowledge" in query_domains:
            domain_focus.append("当前优先按维修知识代理思路工作：先关键参数，再步骤，再风险。")
        if "parts_inventory" in query_domains:
            domain_focus.append("当前优先按配件顾问代理思路工作：先推荐件，再替代件，再风险。")
        if (business_context.get("store_overview") or {}).get("recent_orders"):
            domain_focus.append("当前可视为店务值班场景：优先交付、报价、施工节奏。")
        if domain_focus:
            sections.append("\n".join(domain_focus))

        allowed_tools = [
            "BFF 业务接口",
            "AI 文档解析链路",
            "知识库检索",
            "会话记忆与长期记忆",
            "本地 skills 匹配与注入",
        ]
        sections.append("当前保留的 runtime 能力：" + "、".join(allowed_tools) + "。")

        if docs:
            for name in ["AGENTS.md", "SOUL.md", "TOOLS.md", "HEARTBEAT.md"]:
                text = docs.get(name)
                if text:
                    sections.append(f"{name} 摘要:\n{text[:1200]}")

        return "\n\n".join(item.strip() for item in sections if item.strip())

    def _read_tasks(self) -> List[AgentTask]:
        if not self.tasks_path.exists():
            return []
        try:
            payload = json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        tasks: List[AgentTask] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            task_id = str(item.get("id") or "").strip()
            title = str(item.get("title") or "").strip()
            if not task_id or not title:
                continue
            tasks.append(
                AgentTask(
                    task_id=task_id,
                    title=title,
                    status=str(item.get("status") or "pending"),
                    source=str(item.get("source") or "manual"),
                    payload=item.get("payload") or {},
                    created_at=str(item.get("created_at") or datetime.now(timezone.utc).isoformat()),
                    updated_at=str(item.get("updated_at") or datetime.now(timezone.utc).isoformat()),
                )
            )
        return tasks

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [item.to_dict() for item in self._read_tasks()]

    def upsert_task(
        self,
        task_id: str,
        title: str,
        *,
        status: str = "pending",
        source: str = "manual",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_id = str(task_id or "").strip()
        normalized_title = str(title or "").strip()
        if not normalized_id or not normalized_title:
            raise ValueError("task_id and title are required")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            tasks = self._read_tasks()
            existing = next((item for item in tasks if item.task_id == normalized_id), None)
            if existing:
                existing.title = normalized_title
                existing.status = status
                existing.source = source
                existing.payload = dict(payload or {})
                existing.updated_at = now
                target = existing
            else:
                target = AgentTask(
                    task_id=normalized_id,
                    title=normalized_title,
                    status=status,
                    source=source,
                    payload=dict(payload or {}),
                    created_at=now,
                    updated_at=now,
                )
                tasks.append(target)
            self.tasks_path.write_text(
                json.dumps([item.to_dict() for item in tasks], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return target.to_dict()
