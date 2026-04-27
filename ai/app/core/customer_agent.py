from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re


@dataclass(frozen=True)
class AgentTool:
    tool_id: str
    name: str
    domain: str
    mode: str
    risk_level: str
    requires_confirmation: bool
    description: str
    endpoint_hint: str
    required_context: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "domain": self.domain,
            "mode": self.mode,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
            "description": self.description,
            "endpoint_hint": self.endpoint_hint,
            "required_context": list(self.required_context),
        }


def _tool(
    tool_id: str,
    name: str,
    domain: str,
    mode: str,
    risk_level: str,
    requires_confirmation: bool,
    description: str,
    endpoint_hint: str,
    required_context: Optional[List[str]] = None,
) -> AgentTool:
    return AgentTool(
        tool_id=tool_id,
        name=name,
        domain=domain,
        mode=mode,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        description=description,
        endpoint_hint=endpoint_hint,
        required_context=required_context or [],
    )


DEFAULT_TOOLS: List[AgentTool] = [
    _tool(
        "read_customer_profile",
        "Read Customer Profile",
        "customer",
        "read",
        "low",
        False,
        "Query customer profile, vehicle links, and latest service history.",
        "GET /ai/ops/context",
        ["customer_name|phone|customer_id"],
    ),
    _tool(
        "read_vehicle_profile",
        "Read Vehicle Profile",
        "vehicle",
        "read",
        "low",
        False,
        "Query vehicle baseline, maintenance intervals, and linked work orders.",
        "GET /ai/ops/context",
        ["plate|vehicle_id"],
    ),
    _tool(
        "read_work_order_status",
        "Read Work Order Status",
        "work_order",
        "read",
        "low",
        False,
        "Query work order status, quote snapshot, and next action node.",
        "GET /ai/ops/context",
        ["work_order_id|work_order_uuid"],
    ),
    _tool(
        "read_manual_knowledge",
        "Read Manual Knowledge",
        "knowledge",
        "read",
        "low",
        False,
        "Retrieve manual procedures, sections, and torque references.",
        "POST /kb/query",
        ["model_id|query"],
    ),
    _tool(
        "read_catalog_specs",
        "Read Catalog Specs",
        "catalog",
        "read",
        "low",
        False,
        "Retrieve standardized catalog specs for the selected model.",
        "GET /mp/catalog/vehicle-models/{id}/specs",
        ["model_id"],
    ),
    _tool(
        "read_shop_products",
        "Read Shop Products",
        "shop",
        "read",
        "low",
        False,
        "Retrieve matching shop products and consumables.",
        "GET /mp/customer/shop/products",
        ["vehicle_id"],
    ),
    _tool(
        "write_appointment_draft",
        "Write Appointment Draft",
        "appointment",
        "write",
        "medium",
        False,
        "Create or update appointment draft entries.",
        "POST /mp/customer/appointments/draft",
        ["vehicle_id|plate", "service_items"],
    ),
    _tool(
        "write_work_order_note",
        "Write Work Order Note",
        "work_order",
        "write",
        "medium",
        False,
        "Append notes and follow-up context to an existing work order.",
        "POST /mp/workorders/{id}/notes",
        ["work_order_id|work_order_uuid", "note"],
    ),
    _tool(
        "write_quote_draft",
        "Write Quote Draft",
        "quote",
        "write",
        "high",
        True,
        "Create quote draft from recommended services and parts.",
        "POST /ai/ops/write-command (quote_draft)",
        ["vehicle_id|work_order_id", "service_items"],
    ),
    _tool(
        "write_work_order_create",
        "Write Work Order",
        "work_order",
        "write",
        "high",
        True,
        "Create a new work order record.",
        "POST /work-orders",
        ["customer_id", "vehicle_id", "summary"],
    ),
    _tool(
        "write_manual_ingest_pipeline",
        "Write Manual Ingest Pipeline",
        "knowledge",
        "write",
        "high",
        True,
        "Run manual upload, AI parse, model bind, specs import, segment materialization, and service sync.",
        "POST /mp/knowledge/* pipeline",
        ["model_id|catalog_model_id", "document_id|manual_file_path|manual_file_url"],
    ),
    _tool(
        "write_knowledge_import",
        "Write Knowledge Import",
        "knowledge",
        "write",
        "high",
        True,
        "Import confirmed specs and procedures to catalog model.",
        "POST /mp/knowledge/parse-jobs/{job_id}/import-confirmed-specs",
        ["job_id", "model_id"],
    ),
    _tool(
        "database_schema",
        "Database Schema",
        "database",
        "read",
        "low",
        False,
        "Inspect every table and field in the BFF or Odoo database.",
        "POST /ai/ops/actions (database_schema)",
        ["target_database"],
    ),
    _tool(
        "database_select",
        "Database Select",
        "database",
        "read",
        "medium",
        False,
        "Query arbitrary tables and columns through controlled filters.",
        "POST /ai/ops/actions (database_select)",
        ["target_database", "table"],
    ),
    _tool(
        "database_insert",
        "Database Insert",
        "database",
        "write",
        "high",
        True,
        "Insert records into arbitrary tables after intent is clear.",
        "POST /ai/ops/actions (database_insert)",
        ["target_database", "table", "values"],
    ),
    _tool(
        "database_update",
        "Database Update",
        "database",
        "write",
        "high",
        True,
        "Update arbitrary fields in arbitrary tables with explicit filters.",
        "POST /ai/ops/actions (database_update)",
        ["target_database", "table", "values", "filters"],
    ),
    _tool(
        "database_delete_plan",
        "Database Delete Plan",
        "database",
        "write",
        "critical",
        True,
        "Create a deletion preview and confirmation token before deleting records.",
        "POST /ai/ops/actions (database_delete_plan)",
        ["target_database", "table", "filters"],
    ),
    _tool(
        "database_delete_confirm",
        "Database Delete Confirm",
        "database",
        "write",
        "critical",
        True,
        "Execute a deletion only after the user provides the confirmation token.",
        "POST /ai/ops/actions (database_delete_confirm)",
        ["confirmation_token"],
    ),
    _tool(
        "database_undo",
        "Database Undo",
        "database",
        "write",
        "critical",
        True,
        "Undo a prior AI database insert, update, or confirmed delete by audit undo_id.",
        "POST /ai/ops/actions (database_undo)",
        ["undo_id"],
    ),
]


INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": "manual_ingest_pipeline",
        "pattern": r"(维修手册|手册识别|识别手册|导入手册|manual ingest|parse manual|ocr manual)",
        "tool_ids": [
            "write_manual_ingest_pipeline",
            "write_knowledge_import",
        ],
    },
    {
        "intent": "create_quote_draft",
        "pattern": r"(报价草稿|生成报价|quote draft|quote)",
        "tool_ids": ["read_work_order_status", "read_shop_products", "write_quote_draft"],
    },
    {
        "intent": "create_appointment",
        "pattern": r"(预约|appointment)",
        "tool_ids": ["read_vehicle_profile", "write_appointment_draft"],
    },
    {
        "intent": "create_work_order",
        "pattern": r"(新建工单|创建工单|create work order)",
        "tool_ids": ["read_customer_profile", "read_vehicle_profile", "write_work_order_create"],
    },
    {
        "intent": "update_work_order_note",
        "pattern": r"(工单备注|补备注|note)",
        "tool_ids": ["read_work_order_status", "write_work_order_note"],
    },
    {
        "intent": "manual_guidance",
        "pattern": r"(维修手册|扭矩|规格|怎么修|manual|torque|spec)",
        "tool_ids": ["read_manual_knowledge", "read_catalog_specs"],
    },
    {
        "intent": "database_admin",
        "pattern": r"(database|sql|table|field|column|schema|数据库|数据表|字段|查询表|修改字段|新增字段|删除记录|删数据)",
        "tool_ids": [
            "database_schema",
            "database_select",
            "database_insert",
            "database_update",
            "database_delete_plan",
            "database_delete_confirm",
            "database_undo",
        ],
    },
]


class CustomerServiceAgent:
    def __init__(self, workspace_root: Path, openclaw_workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root
        self.openclaw_workspace_root = openclaw_workspace_root
        self.policy_path = self.workspace_root / "customer_agent_policy.json"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._tools: Dict[str, AgentTool] = {item.tool_id: item for item in DEFAULT_TOOLS}
        self._ensure_policy_file()

    def _ensure_policy_file(self) -> None:
        if self.policy_path.exists():
            return
        payload = {
            "agent_id": "drmoto_customer_service_agent",
            "version": "1.0",
            "maturity_target": "production_stable",
            "write_guard": {
                "high_risk_requires_confirmation": True,
                "critical_write_blocked_without_confirmation": True,
            },
            "tools": [item.to_dict() for item in self._tools.values()],
        }
        self.policy_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def list_tools(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in sorted(self._tools.values(), key=lambda row: (row.domain, row.tool_id))]

    def _match_intent(self, message: str) -> Dict[str, Any]:
        text = str(message or "").strip()
        for rule in INTENT_RULES:
            try:
                if re.search(rule["pattern"], text, flags=re.IGNORECASE):
                    return dict(rule)
            except re.error:
                continue
        return {
            "intent": "general_query",
            "tool_ids": ["read_customer_profile", "read_vehicle_profile", "read_work_order_status"],
        }

    @staticmethod
    def _missing_context(tool: AgentTool, context: Dict[str, Any]) -> List[str]:
        missing: List[str] = []
        lowered_keys = {str(key).lower() for key in context.keys()}
        for requirement in tool.required_context:
            choices = [str(item).strip().lower() for item in requirement.split("|") if str(item).strip()]
            if not choices:
                continue
            if not any(choice in lowered_keys for choice in choices):
                missing.append(requirement)
        return missing

    def plan(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        safe_context = context or {}
        rule = self._match_intent(message)
        steps: List[Dict[str, Any]] = []
        risk_order = {"low": 1, "medium": 2, "high": 3}
        max_risk = "low"
        requires_confirmation = False
        blocked = False
        blocked_reason = ""

        for tool_id in rule.get("tool_ids") or []:
            tool = self._tools.get(str(tool_id))
            if not tool:
                continue
            missing = self._missing_context(tool, safe_context)
            if risk_order.get(tool.risk_level, 1) > risk_order.get(max_risk, 1):
                max_risk = tool.risk_level
            if tool.requires_confirmation:
                requires_confirmation = True
            if tool.mode == "write" and tool.risk_level == "high" and tool.requires_confirmation:
                blocked = True
                blocked_reason = "requires_user_confirmation"
            steps.append(
                {
                    "tool_id": tool.tool_id,
                    "name": tool.name,
                    "domain": tool.domain,
                    "mode": tool.mode,
                    "risk_level": tool.risk_level,
                    "requires_confirmation": tool.requires_confirmation,
                    "endpoint_hint": tool.endpoint_hint,
                    "missing_context": missing,
                }
            )

        return {
            "agent_id": "drmoto_customer_service_agent",
            "intent": rule.get("intent") or "general_query",
            "risk_level": max_risk,
            "requires_confirmation": requires_confirmation,
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "steps": steps,
        }

    def openclaw_reference(self) -> Dict[str, Any]:
        root = self.openclaw_workspace_root
        if not root or not root.exists():
            return {"connected": False}
        files = ["AGENTS.md", "SOUL.md", "TOOLS.md", "HEARTBEAT.md", "MEMORY.md"]
        loaded: Dict[str, int] = {}
        for name in files:
            path = root / name
            if path.exists():
                try:
                    loaded[name] = len(path.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    loaded[name] = 0
        return {"connected": True, "workspace_root": str(root), "loaded_docs": loaded}

    def bootstrap_from_openclaw(self, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
        source_root = workspace_root or self.openclaw_workspace_root
        if not source_root or not source_root.exists():
            return {"imported": False, "reason": "workspace_not_found"}

        imported: Dict[str, int] = {}
        for name in ["AGENTS.md", "SOUL.md", "TOOLS.md", "HEARTBEAT.md"]:
            source_path = source_root / name
            if not source_path.exists():
                continue
            text = source_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            # Keep imports compact so runtime prompts stay focused on customer-service behavior.
            compact = text[:4000].strip()
            target_path = self.workspace_root / f"OPENCLAW_{name}"
            target_path.write_text(compact + "\n", encoding="utf-8")
            imported[name] = len(compact)
        return {
            "imported": bool(imported),
            "source_root": str(source_root),
            "files": imported,
        }
