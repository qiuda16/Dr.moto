from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from difflib import SequenceMatcher
import logging
import requests
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
import io
from pypdf import PdfReader, PdfWriter

from ..core.db import get_db, SessionLocal
from ..models import (
    Vehicle,
    Procedure,
    ProcedureStep,
    VehicleCatalogModel,
    VehicleCatalogSpec,
    VehicleKnowledgeDocument,
    VehicleKnowledgeParseJob,
    VehicleKnowledgeParsePage,
    VehicleKnowledgeSegment,
)
from ..integrations.odoo import odoo_client
from ..integrations.obj_storage import obj_storage
from ..core.config import settings
from ..core.text import build_storage_object_name, normalize_text
from ..core.security import require_roles
from ..schemas.auth import User
from .catalog import _ensure_baseline_service_items_for_model, _normalize_year_to

router = APIRouter(prefix="/mp/knowledge", tags=["Knowledge Base"])
logger = logging.getLogger("bff")

KNOWLEDGE_UPLOAD_MAX_BYTES = 120 * 1024 * 1024
KNOWLEDGE_TITLE_MAX = 160
KNOWLEDGE_CATEGORY_MAX = 40
KNOWLEDGE_NOTES_MAX = 2000


def _catalog_vehicle_key(model_id: int) -> str:
    return f"CATALOG_MODEL:{model_id}"


def _validate_bounded_text(value: Optional[str], field_name: str, max_length: int, default: Optional[str] = None) -> Optional[str]:
    normalized = normalize_text(value)
    if normalized in (None, ""):
        return default
    if len(normalized) > max_length:
        raise HTTPException(status_code=400, detail=f"{field_name} is too long")
    return normalized


def _split_match_tokens(value: str | None) -> list[str]:
    normalized = _normalize_match_text(value)
    return [token for token in re.split(r"[\s\-_/]+", normalized) if token]


def _match_score(query: str, target: str | None) -> float:
    query_key = _normalize_match_text(query)
    target_key = _normalize_match_text(target)
    if not query_key or not target_key:
        return 0.0
    if query_key == target_key:
        return 120.0
    score = 0.0
    if target_key.startswith(query_key):
        score += 80.0
    elif query_key in target_key:
        score += 55.0
    query_tokens = _split_match_tokens(query_key)
    target_tokens = _split_match_tokens(target_key)
    for token in query_tokens:
        if token in target_tokens:
            score += 18.0
        elif any(item.startswith(token) for item in target_tokens):
            score += 12.0
        elif token in target_key:
            score += 8.0
    score += SequenceMatcher(None, query_key, target_key).ratio() * 20.0
    return score


def _document_search_rank(
    payload: dict,
    row: Optional[VehicleKnowledgeDocument],
    latest_job: Optional[VehicleKnowledgeParseJob],
    model: Optional[VehicleCatalogModel],
    query: str,
) -> tuple[float, int, str]:
    score = 0.0
    score += _match_score(query, row.title if row else payload.get("title")) * 1.5
    score += _match_score(query, row.file_name if row else payload.get("file_name")) * 1.3
    score += _match_score(query, row.notes if row else payload.get("notes"))
    score += _match_score(query, row.category if row else payload.get("category")) * 0.9
    if model:
        score += _match_score(query, model.brand) * 1.1
        score += _match_score(query, model.model_name) * 1.35
        score += _match_score(query, f"{model.brand} {model.model_name}") * 1.25
    candidate = payload.get("catalog_candidate") or {}
    score += _match_score(query, candidate.get("brand")) * 0.95
    score += _match_score(query, candidate.get("model_name")) * 1.1
    if ((row.review_status if row else payload.get("review_status")) or "pending_review") == "pending_review":
        score += 2.0
    if latest_job and latest_job.status == "processing":
        score -= 1.0
    created_weight = int((row.id if row else payload.get("id")) or 0)
    return (score, created_weight, _normalize_match_text(row.title if row else payload.get("title")))

class VehicleSchema(BaseModel):
    key: str
    make: str
    model: str
    year_from: int
    
class StepSchema(BaseModel):
    step_order: int
    instruction: str
    required_tools: Optional[str]
    torque_spec: Optional[str]

class ProcedureSchema(BaseModel):
    id: int
    name: str
    steps: List[StepSchema]


class ManualProcedureCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ManualProcedureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ManualStepCreate(BaseModel):
    step_order: int
    instruction: str
    required_tools: Optional[str] = None
    torque_spec: Optional[str] = None
    hazards: Optional[str] = None


class ManualStepUpdate(BaseModel):
    step_order: Optional[int] = None
    instruction: Optional[str] = None
    required_tools: Optional[str] = None
    torque_spec: Optional[str] = None
    hazards: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    id: int
    model_id: int
    title: str
    file_name: str
    object_name: Optional[str] = None
    file_url: str
    download_url: Optional[str] = None
    file_type: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    review_status: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    catalog_confirmation_status: Optional[str] = None
    catalog_candidate: Optional[dict] = None
    catalog_confirmed_model_id: Optional[int] = None
    catalog_confirmed_model_info: Optional[dict] = None
    catalog_confirmed_by: Optional[str] = None
    catalog_confirmed_at: Optional[datetime] = None
    uploaded_by: Optional[str] = None
    model_info: Optional[dict] = None
    latest_parse_job: Optional[dict] = None


class KnowledgeDocumentReviewUpdate(BaseModel):
    review_status: str
    review_notes: Optional[str] = None


class KnowledgeDocumentCatalogConfirmationUpdate(BaseModel):
    action: str
    model_id: Optional[int] = None
    brand: Optional[str] = None
    model_name: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    displacement_cc: Optional[int] = None
    default_engine_code: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class KnowledgeParseJobResponse(BaseModel):
    id: int
    document_id: int
    model_id: int
    status: str
    provider: Optional[str] = None
    parser_version: Optional[str] = None
    page_count: Optional[int] = None
    extracted_sections: Optional[int] = None
    extracted_specs: Optional[int] = None
    processed_batches: Optional[int] = None
    total_batches: Optional[int] = None
    progress_percent: Optional[int] = None
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    summary_json: Optional[dict] = None
    raw_result_json: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class KnowledgeParsePageResponse(BaseModel):
    id: int
    job_id: int
    document_id: int
    page_number: int
    page_label: Optional[str] = None
    text_content: Optional[str] = None
    summary: Optional[str] = None
    blocks_json: Optional[list] = None
    specs_json: Optional[list] = None
    procedures_json: Optional[list] = None
    confidence: Optional[float] = None


class KnowledgeParseJobDetailResponse(KnowledgeParseJobResponse):
    pages: List[KnowledgeParsePageResponse] = []


class KnowledgeParseJobResultUpdate(BaseModel):
    applicability: Optional[dict] = None
    sections: Optional[list] = None
    specs: Optional[list] = None
    procedures: Optional[list] = None
    review_notes: Optional[str] = None


class KnowledgeParsePageUpdate(BaseModel):
    summary: Optional[str] = None
    text_content: Optional[str] = None
    specs_json: Optional[list] = None
    procedures_json: Optional[list] = None


class KnowledgeSegmentResponse(BaseModel):
    id: int
    model_id: int
    source_document_id: int
    source_job_id: int
    chapter_no: Optional[str] = None
    title: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    segment_document_id: Optional[int] = None
    procedure_id: Optional[int] = None
    review_status: str
    notes: Optional[str] = None
    segment_document: Optional[dict] = None
    procedure: Optional[dict] = None


def _job_to_dict(row: VehicleKnowledgeParseJob) -> dict:
    return {
        "id": row.id,
        "document_id": row.document_id,
        "model_id": row.model_id,
        "status": row.status,
        "provider": row.provider,
        "parser_version": row.parser_version,
        "page_count": row.page_count,
        "extracted_sections": row.extracted_sections,
        "extracted_specs": row.extracted_specs,
        "processed_batches": row.processed_batches,
        "total_batches": row.total_batches,
        "progress_percent": row.progress_percent,
        "progress_message": row.progress_message,
        "error_message": row.error_message,
        "summary_json": row.summary_json,
        "raw_result_json": row.raw_result_json,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


def _page_to_dict(row: VehicleKnowledgeParsePage) -> dict:
    return {
        "id": row.id,
        "job_id": row.job_id,
        "document_id": row.document_id,
        "page_number": row.page_number,
        "page_label": row.page_label,
        "text_content": row.text_content,
        "summary": row.summary,
        "blocks_json": row.blocks_json or [],
        "specs_json": row.specs_json or [],
        "procedures_json": row.procedures_json or [],
        "confidence": row.confidence,
    }


def _document_to_dict(
    row: VehicleKnowledgeDocument,
    latest_job: Optional[VehicleKnowledgeParseJob] = None,
    model: Optional[VehicleCatalogModel] = None,
    confirmed_model: Optional[VehicleCatalogModel] = None,
) -> dict:
    candidate = _ensure_dict(row.catalog_candidate_json)
    if not candidate and latest_job:
        candidate = _infer_catalog_candidate_from_job(latest_job, [])
    return {
        "id": row.id,
        "model_id": row.model_id,
        "title": row.title,
        "file_name": row.file_name,
        "object_name": row.object_name,
        "file_url": row.file_url,
        "download_url": f"/api/mp/knowledge/documents/{row.id}/download",
        "file_type": row.file_type,
        "category": row.category,
        "notes": row.notes,
        "review_status": row.review_status,
        "review_notes": row.review_notes,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": row.reviewed_at,
        "catalog_confirmation_status": row.catalog_confirmation_status,
        "catalog_candidate": candidate or None,
        "catalog_confirmed_model_id": row.catalog_confirmed_model_id,
        "catalog_confirmed_model_info": (
            {
                "id": confirmed_model.id,
                "brand": confirmed_model.brand,
                "model_name": confirmed_model.model_name,
                "year_from": confirmed_model.year_from,
                "year_to": confirmed_model.year_to,
            }
            if confirmed_model
            else None
        ),
        "catalog_confirmed_by": row.catalog_confirmed_by,
        "catalog_confirmed_at": row.catalog_confirmed_at,
        "uploaded_by": row.uploaded_by,
        "model_info": (
            {
                "id": model.id,
                "brand": model.brand,
                "model_name": model.model_name,
                "year_from": model.year_from,
                "year_to": model.year_to,
            }
            if model
            else None
        ),
        "latest_parse_job": _job_to_dict(latest_job) if latest_job else None,
    }


def _apply_catalog_candidate_snapshot(
    document: VehicleKnowledgeDocument,
    latest_job: Optional[VehicleKnowledgeParseJob],
    pages: Optional[list[VehicleKnowledgeParsePage]] = None,
) -> dict:
    candidate = _ensure_dict(document.catalog_candidate_json)
    if latest_job:
        candidate = _infer_catalog_candidate_from_job(latest_job, pages or [])
    document.catalog_candidate_json = candidate or None
    return candidate


def _confirmed_model_to_dict(row: Optional[VehicleCatalogModel]) -> Optional[dict]:
    if not row:
        return None
    return {
        "id": row.id,
        "brand": row.brand,
        "model_name": row.model_name,
        "year_from": row.year_from,
        "year_to": row.year_to,
        "displacement_cc": row.displacement_cc,
        "category": row.category,
        "fuel_type": row.fuel_type,
        "default_engine_code": row.default_engine_code,
        "source": row.source,
    }


def _set_document_catalog_confirmation(
    document: VehicleKnowledgeDocument,
    target_model: VehicleCatalogModel,
    current_user: User,
) -> None:
    document.model_id = target_model.id
    document.catalog_confirmation_status = "confirmed"
    document.catalog_confirmed_model_id = target_model.id
    document.catalog_confirmed_by = current_user.username
    document.catalog_confirmed_at = datetime.now(timezone.utc)


def _require_catalog_confirmation(document: VehicleKnowledgeDocument) -> None:
    if (document.catalog_confirmation_status or "pending_confirmation") != "confirmed":
        raise HTTPException(status_code=400, detail="请先确认这份手册对应的品牌、年款和车型，再继续入库")


def _procedure_to_dict(proc: Procedure, steps: list[ProcedureStep] | None = None) -> dict:
    ordered_steps = steps or []
    return {
        "id": proc.id,
        "name": proc.name,
        "description": proc.description,
        "steps_count": len(ordered_steps),
        "steps": [
            {
                "id": step.id,
                "step_order": step.step_order,
                "instruction": step.instruction,
                "required_tools": step.required_tools,
                "torque_spec": step.torque_spec,
                "hazards": step.hazards,
            }
            for step in ordered_steps
        ],
    }


def _segment_to_dict(
    row: VehicleKnowledgeSegment,
    segment_document: VehicleKnowledgeDocument | None = None,
    procedure: Procedure | None = None,
    steps: list[ProcedureStep] | None = None,
) -> dict:
    return {
        "id": row.id,
        "model_id": row.model_id,
        "source_document_id": row.source_document_id,
        "source_job_id": row.source_job_id,
        "chapter_no": row.chapter_no,
        "title": row.title,
        "start_page": row.start_page,
        "end_page": row.end_page,
        "segment_document_id": row.segment_document_id,
        "procedure_id": row.procedure_id,
        "review_status": row.review_status,
        "notes": row.notes,
        "segment_document": _document_to_dict(segment_document) if segment_document else None,
        "procedure": _procedure_to_dict(procedure, steps or []) if procedure else None,
    }


def _ensure_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _ensure_list(value) -> list:
    return value if isinstance(value, list) else []


def _clean_text_value(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _dedupe_rows(rows: list[dict], keys: list[str]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(_clean_text_value(row.get(item)).lower() for item in keys)
        if not any(key) or key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _collect_tool_rows(procedures: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in procedures:
        required_tools = item.get("required_tools")
        if isinstance(required_tools, list):
            values = required_tools
        else:
            values = re.split(r"[、,，;；]\s*", str(required_tools or ""))
        for value in values:
            name = _clean_text_value(value)
            if name:
                rows.append({"name": name})
    return _dedupe_rows(rows, ["name"])


def _collect_nested_rows(procedures: list[dict], field_name: str, keys: list[str]) -> list[dict]:
    rows: list[dict] = []
    for item in procedures:
        for nested in _ensure_list(item.get(field_name)):
            if isinstance(nested, dict):
                rows.append(dict(nested))
    return _dedupe_rows(rows, keys)


def _rebuild_manual_views(summary: dict, normalized: dict) -> tuple[dict, dict]:
    specs = [item for item in _ensure_list(summary.get("specs")) if isinstance(item, dict)]
    procedures = [item for item in _ensure_list(summary.get("procedures")) if isinstance(item, dict)]
    torque_specs = [item for item in specs if str(item.get("type") or "").lower() == "torque"]
    fluid_specs = [item for item in specs if str(item.get("type") or "").lower() == "capacity"]
    pressure_specs = [item for item in specs if str(item.get("type") or "").lower() == "pressure"]
    voltage_specs = [item for item in specs if str(item.get("type") or "").lower() == "voltage"]
    clearance_specs = [item for item in specs if str(item.get("type") or "").lower() == "clearance"]
    tools = _collect_tool_rows(procedures)
    fasteners = _collect_nested_rows(procedures, "fasteners", ["name", "size", "drive_type"])
    materials = _collect_nested_rows(procedures, "materials", ["name", "value", "unit"])
    filters = [item for item in materials if "滤" in _clean_text_value(item.get("name"))]
    fluids = [item for item in materials if _clean_text_value(item.get("name")) in {"机油", "冷却液", "制动液", "前叉油", "齿轮油"}]
    consumables = [item for item in materials if item not in filters and item not in fluids]
    step_cards = _ensure_list(_ensure_dict(normalized.get("technician_view")).get("step_cards"))
    if not step_cards:
        step_cards = [
            {
                "step_order": item.get("step_order") or index,
                "section_title": item.get("section_title"),
                "instruction": item.get("instruction"),
                "instruction_original": item.get("instruction_original") or item.get("instruction"),
                "required_tools": _collect_tool_rows([item]),
                "torque_specs": [],
                "related_specs": [],
                "materials": _ensure_list(item.get("materials")),
                "fasteners": _ensure_list(item.get("fasteners")),
                "action_type": item.get("action_type"),
                "target_component": item.get("target_component"),
                "tooling_summary": item.get("tooling_summary"),
                "step_purpose": item.get("step_purpose"),
                "input_requirements": _ensure_list(item.get("input_requirements")),
                "preconditions": _ensure_list(item.get("preconditions")),
                "setup_conditions": _ensure_list(item.get("setup_conditions")),
                "control_points": _ensure_list(item.get("control_points")),
                "acceptance_checks": _ensure_list(item.get("acceptance_checks")),
                "completion_definition": _ensure_list(item.get("completion_definition")),
                "output_results": _ensure_list(item.get("output_results")),
                "reassembly_requirements": _ensure_list(item.get("reassembly_requirements")),
                "caution_notes": _ensure_list(item.get("caution_notes")),
                "common_failure_modes": _ensure_list(item.get("common_failure_modes")),
                "criticality": item.get("criticality"),
                "executor_role": item.get("executor_role"),
                "support_role": item.get("support_role"),
                "verification_role": item.get("verification_role"),
                "record_requirements": _ensure_list(item.get("record_requirements")),
                "source_page": item.get("page_number"),
            }
            for index, item in enumerate(procedures, start=1)
        ]
    critical_steps = [item for item in step_cards if _clean_text_value(item.get("criticality")) == "critical"][:40]
    normalized["procedures"] = {
        **_ensure_dict(normalized.get("procedures")),
        "steps": procedures,
        "step_cards": step_cards[:200],
        "required_tools": tools,
        "quality_checks": critical_steps,
        "critical_steps": critical_steps,
    }
    normalized["specifications"] = {
        **_ensure_dict(normalized.get("specifications")),
        "torque_specs": torque_specs,
        "top_torque_specs": torque_specs[:40],
        "fluid_specs": fluid_specs,
        "pressure_specs": pressure_specs,
        "voltage_specs": voltage_specs,
        "clearance_specs": clearance_specs,
        "fastener_specs": fasteners,
    }
    normalized["parts_and_materials"] = {
        **_ensure_dict(normalized.get("parts_and_materials")),
        "parts": _ensure_list(_ensure_dict(normalized.get("parts_and_materials")).get("parts")),
        "consumables": consumables,
        "fluids": fluids,
        "filters": filters,
    }
    normalized["technician_view"] = {
        "quick_reference": {
            "torque": torque_specs[:40],
            "fluids": fluid_specs or fluids,
            "filters": filters,
            "fasteners": fasteners,
            "tools": tools,
            "critical_steps": critical_steps,
        },
        "step_cards": step_cards[:200],
    }
    return normalized, {
        "tools": tools,
        "materials": materials,
        "filters": filters,
        "fasteners": fasteners,
        "step_cards": step_cards,
    }


def _recalculate_job_summary(job: VehicleKnowledgeParseJob, pages: list[VehicleKnowledgeParsePage]) -> None:
    raw = _ensure_dict(job.raw_result_json)
    summary = _ensure_dict(job.summary_json)
    page_dicts = [_page_to_dict(page) for page in pages]
    all_specs: list[dict] = []
    all_procedures: list[dict] = []
    for page in page_dicts:
        for item in _ensure_list(page.get("specs_json")):
            if isinstance(item, dict):
                merged = dict(item)
                merged.setdefault("page_number", page.get("page_number"))
                all_specs.append(merged)
        for item in _ensure_list(page.get("procedures_json")):
            if isinstance(item, dict):
                merged = dict(item)
                merged.setdefault("page_number", page.get("page_number"))
                all_procedures.append(merged)
    summary["specs"] = all_specs
    summary["procedures"] = all_procedures
    summary["sections"] = _ensure_list(summary.get("sections"))
    job.summary_json = summary
    normalized = _ensure_dict(raw.get("normalized_manual"))
    normalized.setdefault("applicability", {})
    normalized, technician_refs = _rebuild_manual_views(summary, normalized)
    raw["normalized_manual"] = normalized
    manual_template = _ensure_dict(raw.get("manual_template"))
    completion = []
    applicability = _ensure_dict(normalized.get("applicability"))
    completion.append({
        "label": "适用车型",
        "is_complete": bool(applicability.get("brand") and applicability.get("model_name")),
        "present_children": [key for key in ["brand", "model_name", "year_range", "engine_code"] if applicability.get(key)],
        "missing_children": [key for key in ["brand", "model_name", "year_range", "engine_code"] if not applicability.get(key)],
    })
    completion.append({
        "label": "章节结构",
        "is_complete": bool(summary.get("sections")),
        "present_children": [str(item.get("title") or item.get("label") or "").strip() for item in _ensure_list(summary.get("sections")) if isinstance(item, dict) and (item.get("title") or item.get("label"))],
        "missing_children": [],
    })
    completion.append({
        "label": "关键规格",
        "is_complete": bool(all_specs),
        "present_children": [str(item.get("label") or item.get("type") or "").strip() for item in all_specs[:12]],
        "missing_children": [],
    })
    completion.append({
        "label": "施工步骤",
        "is_complete": bool(all_procedures),
        "present_children": [f"步骤{index + 1}" for index, _ in enumerate(all_procedures[:12])],
        "missing_children": [],
    })
    completion.append({
        "label": "维修快查视图",
        "is_complete": bool(technician_refs.get("step_cards") or technician_refs.get("fasteners") or technician_refs.get("materials")),
        "present_children": [
            *([f"step_cards:{len(technician_refs.get('step_cards') or [])}"] if technician_refs.get("step_cards") else []),
            *([f"fasteners:{len(technician_refs.get('fasteners') or [])}"] if technician_refs.get("fasteners") else []),
            *([f"materials:{len(technician_refs.get('materials') or [])}"] if technician_refs.get("materials") else []),
            *([f"tools:{len(technician_refs.get('tools') or [])}"] if technician_refs.get("tools") else []),
        ],
        "missing_children": [
            *([] if technician_refs.get("step_cards") else ["step_cards"]),
            *([] if technician_refs.get("fasteners") else ["fasteners"]),
            *([] if technician_refs.get("materials") else ["materials"]),
        ],
    })
    ready_count = sum(1 for item in completion if item.get("is_complete"))
    manual_template["completion"] = completion
    manual_template["completion_ratio"] = ready_count / max(len(completion), 1)
    raw["manual_template"] = manual_template
    job.raw_result_json = raw
    job.extracted_sections = len(_ensure_list(summary.get("sections")))
    job.extracted_specs = len(all_specs)


def _normalize_spec_key(label: str | None, spec_type: str | None) -> str:
    base = (label or spec_type or "spec").strip().lower()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in base)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "spec"


def _spec_rank(item: dict) -> tuple[int, int, int]:
    label = str(item.get("label") or "")
    source_text = str(item.get("source_text") or "")
    value = str(item.get("value") or "")
    return (
        1 if any(token in label for token in ("螺栓", "螺母", "油压", "机油", "游隙", "气门")) else 0,
        len(source_text),
        len(value),
    )


def _preferred_specs(items: list[dict]) -> list[dict]:
    preferred: dict[tuple[str, str, str, str | None], dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("type") or ""),
            str(item.get("value") or ""),
            str(item.get("unit") or ""),
            None if item.get("page_number") is None else str(item.get("page_number")),
        )
        current = preferred.get(key)
        if current is None or _spec_rank(item) > _spec_rank(current):
            preferred[key] = item
    return list(preferred.values())


def _slugify_segment_title(value: str | None) -> str:
    base = _normalize_spec_key(value or "segment", None)
    return base[:80] or "segment"


def _segment_file_name(chapter_no: str | None, title: str, source_file_name: str | None) -> str:
    suffix = ".pdf"
    if source_file_name and "." in source_file_name:
        suffix = "." + source_file_name.split(".")[-1].lower()
    prefix = f"{chapter_no.strip()}_" if chapter_no else ""
    return f"{prefix}{_slugify_segment_title(title)}{suffix}"


def _clean_outline_title(title: str | None) -> str:
    text = str(title or "").strip()
    if not text:
        return ""
    return (
        text.replace("（小）", "")
        .replace("(小)", "")
        .replace("  ", " ")
        .strip(" -")
        .strip()
    )


def _extract_chapter_no(title: str | None) -> str | None:
    text = _clean_outline_title(title)
    if not text:
        return None
    match = re.match(r"^([0-9]{2,}(?:[A-Za-z0-9._-]+)?)\b", text)
    if match:
        return match.group(1)
    return None


def _extract_outline_nodes(reader: PdfReader) -> list[dict]:
    try:
        outline = reader.outline
    except Exception:
        return []
    nodes: list[dict] = []

    def walk(items, depth: int = 0, parent_id: int | None = None) -> None:
        last_node_id: int | None = None
        for item in items:
            if isinstance(item, list):
                if last_node_id is not None:
                    walk(item, depth + 1, last_node_id)
                continue
            title = _clean_outline_title(getattr(item, "title", None) or str(item))
            try:
                page_number = reader.get_destination_page_number(item) + 1
            except Exception:
                page_number = None
            if not title:
                continue
            node_id = len(nodes)
            nodes.append(
                {
                    "id": node_id,
                    "title": title,
                    "page_number": page_number,
                    "level": depth,
                    "parent_id": parent_id,
                    "children": [],
                    "chapter_no": _extract_chapter_no(title),
                }
            )
            if parent_id is not None and 0 <= parent_id < len(nodes):
                nodes[parent_id]["children"].append(node_id)
            last_node_id = node_id

    if isinstance(outline, list):
        walk(outline)
    return nodes


def _resolve_outline_chapter_no(nodes: list[dict], node: dict) -> str | None:
    current = node
    while current:
        chapter_no = current.get("chapter_no")
        if chapter_no:
            return chapter_no
        parent_id = current.get("parent_id")
        if parent_id is None:
            return None
        current = nodes[parent_id] if 0 <= parent_id < len(nodes) else None
    return None


def _build_segments_from_pdf_outline(reader: PdfReader) -> list[dict]:
    nodes = _extract_outline_nodes(reader)
    if not nodes:
        return []
    page_total = len(reader.pages)
    segments: list[dict] = []
    for index, node in enumerate(nodes):
        start_page = node.get("page_number")
        title = _clean_outline_title(node.get("title"))
        if not title or not start_page:
            continue
        if title in {"封皮", "封面"}:
            continue
        next_start: int | None = None
        for candidate in nodes[index + 1 :]:
            candidate_page = candidate.get("page_number")
            if not candidate_page:
                continue
            if candidate_page <= start_page:
                continue
            if int(candidate.get("level") or 0) <= int(node.get("level") or 0):
                next_start = candidate_page
                break
        end_page = (next_start - 1) if next_start else page_total
        end_page = max(start_page, min(end_page, page_total))
        outline_children = []
        for child_id in node.get("children") or []:
            if 0 <= child_id < len(nodes):
                child = nodes[child_id]
                outline_children.append(
                    {
                        "title": _clean_outline_title(child.get("title")),
                        "page_number": child.get("page_number"),
                        "level": child.get("level"),
                    }
                )
        segments.append(
            {
                "chapter_no": _resolve_outline_chapter_no(nodes, node),
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
                "toc_page_number": start_page,
                "source": "pdf_outline",
                "outline_children": outline_children,
                "level": node.get("level"),
            }
        )
    return segments


def _extract_steps_from_outline_segment(segment: dict, start_page: int | None, end_page: int | None) -> list[dict]:
    results: list[dict] = []
    children = [item for item in _ensure_list(segment.get("outline_children")) if isinstance(item, dict)]
    if children:
        for index, child in enumerate(children, start=1):
            title = str(child.get("title") or "").strip()
            if not title:
                continue
            page_number = child.get("page_number")
            instruction = title
            if page_number:
                instruction = f"{title}（原手册第 {page_number} 页）"
            results.append(
                {
                    "step_order": index,
                    "instruction": instruction,
                    "required_tools": None,
                    "torque_spec": None,
                    "hazards": None,
                    "page_number": page_number,
                }
            )
    if results:
        return results
    title = str(segment.get("title") or "").strip() or "查看手册原文"
    page_text = f"第 {start_page} - {end_page} 页" if start_page and end_page and end_page != start_page else f"第 {start_page} 页" if start_page else "对应章节"
    return [
        {
            "step_order": 1,
            "instruction": f"打开《{title}》分段 PDF，查看手册原文（{page_text}）。",
            "required_tools": None,
            "torque_spec": None,
            "hazards": None,
            "page_number": start_page,
        }
    ]


def _extract_steps_from_page_range(pages: list[VehicleKnowledgeParsePage], start_page: int | None, end_page: int | None) -> list[dict]:
    if not start_page:
        return []
    results: list[dict] = []
    for page in pages:
        page_no = int(page.page_number or 0)
        if page_no < int(start_page):
            continue
        if end_page and page_no > int(end_page):
            continue
        for item in _ensure_list(page.procedures_json):
            if isinstance(item, dict):
                merged = dict(item)
                merged.setdefault("page_number", page_no)
                results.append(merged)
    deduped: list[dict] = []
    seen: set[tuple[int | None, str]] = set()
    for item in results:
        key = (item.get("page_number"), str(item.get("instruction") or "").strip())
        if not key[1] or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    for index, item in enumerate(deduped, start=1):
        item["step_order"] = index
    return deduped


def _clean_manual_line(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.replace("•", "").replace("·", "").strip(" -:：;；,，")
    return text.strip()


def _line_has_manual_action(text: str) -> bool:
    return bool(re.search(r"(拆卸|拆下|拆开|取下|卸下|分解|检查|点检|测量|清洁|清洗|安装|装配|装回|紧固|拧紧|更换|调整|校准|加注|排放|润滑|确认|复位|启动|记录)", text))


def _line_quality_ok(text: str) -> bool:
    if not text:
        return False
    allowed_chars = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9\s\-/()（）:：;；,.，。%、℃·NmVkPaLml]", text))
    ratio = allowed_chars / max(len(text), 1)
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    if ratio < 0.65:
        return False
    if chinese_count == 0 and not re.search(r"[A-Za-z]{3,}", text):
        return False
    return True


def _line_is_noise(text: str, segment_title: str) -> bool:
    if not text:
        return True
    normalized = _normalize_match_text(text)
    title_key = _normalize_match_text(segment_title)
    if normalized == title_key:
        return True
    if len(text) <= 2:
        return True
    if re.fullmatch(r"[\d./\\\-()（）]+", text):
        return True
    if any(token in text for token in ("目录", "索引", "前言", "专用符号", "使用方法", "记载内容")):
        return True
    if text.startswith("GSX") or text.startswith("SUZUKI"):
        return True
    if re.match(r"^第?\s*\d+\s*页$", text):
        return True
    return False


def _extract_steps_from_segment_text(reader: PdfReader, start_page: int | None, end_page: int | None, segment_title: str) -> list[dict]:
    if not start_page:
        return []
    candidates: list[dict] = []
    seen: set[str] = set()
    numbered_pattern = re.compile(r"^(?:\d+[.)、]|[①②③④⑤⑥⑦⑧⑨⑩])\s*")
    final_page = end_page or start_page
    for page_index in range(start_page - 1, final_page):
        if page_index < 0 or page_index >= len(reader.pages):
            continue
        try:
            page_text = reader.pages[page_index].extract_text() or ""
        except Exception:
            page_text = ""
        if not page_text:
            continue
        for raw_line in page_text.splitlines():
            line = _clean_manual_line(raw_line)
            if not line or _line_is_noise(line, segment_title):
                continue
            is_numbered = bool(numbered_pattern.match(line))
            line = numbered_pattern.sub("", line).strip()
            if not line or _line_is_noise(line, segment_title):
                continue
            if not _line_quality_ok(line):
                continue
            if not is_numbered and not _line_has_manual_action(line):
                continue
            if len(line) < 5:
                continue
            key = _normalize_match_text(line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "step_order": len(candidates) + 1,
                    "instruction": line,
                    "required_tools": None,
                    "torque_spec": None,
                    "hazards": None,
                    "page_number": page_index + 1,
                }
            )
            if len(candidates) >= 10:
                break
        if len(candidates) >= 10:
            break
    return candidates


def _build_semantic_fallback_steps(title: str, start_page: int | None, end_page: int | None) -> list[dict]:
    page_hint = f"第 {start_page}-{end_page} 页" if start_page and end_page and end_page != start_page else (f"第 {start_page} 页" if start_page else "对应章节")
    lower_title = str(title or "").lower()
    templates: list[str]
    if any(token in title for token in ("更换", "换机油", "换机滤", "换刹车油", "刹车片")):
        templates = [
            f"确认《{title}》适用车型、零件规格和施工位置，并打开手册 {page_hint} 对照原文。",
            "按手册顺序拆除影响作业的外部件，注意保护卡扣、密封面和连接线束。",
            "拆下旧件后先检查磨损、渗漏、污染或异常间隙，并记录需要说明给客户的情况。",
            "按原厂要求安装新件或恢复部件，关键紧固位按手册力矩执行，必要时补充油液或润滑。",
            "完工后执行功能确认、渗漏检查和路试或复检，并把结果写入工单和体检记录。",
        ]
    elif any(token in title for token in ("点检", "检查", "诊断", "故障排除")):
        templates = [
            f"确认《{title}》对应系统和检查范围，打开手册 {page_hint} 对照标准值与判定条件。",
            "清洁待检查部位，先做目视检查，再按手册要求测量尺寸、电压、压力或间隙。",
            "把实测值与标准值、极限值逐项比对，判断是否继续使用、调整或更换零件。",
            "如发现异常，继续沿手册给出的关联检查项排查，并记录故障现象和原因。",
            "完成后把检查结论、处理建议和后续复查要求写入工单与车辆档案。",
        ]
    elif any(token in title for token in ("拆卸", "分解")):
        templates = [
            f"确认《{title}》对应总成与拆卸范围，打开手册 {page_hint} 对照拆装顺序。",
            "先断开电源、释放压力或放净相关油液，再拆除妨碍作业的外部件。",
            "按由外到内的顺序拆卸目标总成，做好零件摆放、方向标记和垫片、卡簧位置标识。",
            "拆下后立即检查零件磨损、裂纹、烧蚀或变形，必要时测量关键尺寸。",
            "将可复用件、待更换件和待清洗件分开放置，准备进入清洗、检查或装配工序。",
        ]
    elif any(token in title for token in ("组装", "装配", "安装")):
        templates = [
            f"确认《{title}》对应总成和装配顺序，打开手册 {page_hint} 核对零件方向和注意事项。",
            "装配前清洁零件和结合面，检查密封件、轴承、卡簧、垫片是否符合继续使用条件。",
            "按手册顺序完成预装、定位和总成装回，必要时涂规定的润滑脂、机油或密封胶。",
            "所有关键紧固位按手册规定的扭矩和顺序锁付，装后复查间隙、自由行程和连接状态。",
            "完工后执行功能检查和静态复检，确认无异响、无卡滞、无渗漏后再进入下一工序。",
        ]
    elif any(token in title for token in ("机油", "滤芯", "油压", "油泵")) or any(token in lower_title for token in ("oil", "filter")):
        templates = [
            f"确认《{title}》相关的油液规格、容量、力矩和操作顺序，打开手册 {page_hint} 对照原文。",
            "放油或拆检前先确认发动机温度、放油位置和滤芯、油道部件拆装条件。",
            "拆下相关部件后检查密封圈、滤芯、油道和接触面，必要时清洁杂质与旧胶。",
            "按手册要求更换滤芯、密封件或恢复油路，关键螺栓按规定力矩锁付。",
            "补充规定型号和容量的机油，启动复检油压、渗漏和油位，并记录施工结果。",
        ]
    else:
        templates = [
            f"打开《{title}》分段 PDF，并先对照手册 {page_hint} 明确本章节的作业范围和前置条件。",
            "按照手册给出的准备、拆装、检查和恢复顺序执行，不要跳步省略确认项。",
            "遇到关键尺寸、扭矩、油液、线束或定位要求时，先核对原文后再操作。",
            "施工过程中同步记录异常点、磨损状态和需追加报价或说明给客户的事项。",
            "完工后执行功能复检并把结论写入工单，必要时回看本章节 PDF 原文复核。",
        ]
    return [
        {
            "step_order": index + 1,
            "instruction": instruction,
            "required_tools": None,
            "torque_spec": None,
            "hazards": None,
            "page_number": start_page,
        }
        for index, instruction in enumerate(templates)
    ]


def _latest_jobs_map(db: Session, document_ids: List[int]) -> dict[int, VehicleKnowledgeParseJob]:
    if not document_ids:
        return {}
    rows = (
        db.query(VehicleKnowledgeParseJob)
        .filter(VehicleKnowledgeParseJob.document_id.in_(document_ids))
        .order_by(
            VehicleKnowledgeParseJob.document_id.asc(),
            VehicleKnowledgeParseJob.id.desc(),
        )
        .all()
    )
    latest = {}
    for row in rows:
        if row.document_id not in latest:
            latest[row.document_id] = row
    return latest


def _resolve_object_name(row: VehicleKnowledgeDocument) -> Optional[str]:
    if row.object_name:
        return row.object_name
    if not row.file_url:
        return None
    try:
        parsed = urlparse(row.file_url)
        marker = f"/{settings.MINIO_BUCKET}/"
        if marker in parsed.path:
            return unquote(parsed.path.split(marker, 1)[1])
    except Exception:
        return None
    return None


def _normalize_match_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return "".join(str(value).strip().lower().split())


def _safe_year_range(value) -> tuple[int | None, int | None]:
    if value is None:
        return (None, None)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            year_from = int(value[0]) if value[0] else None
            year_to = int(value[1]) if value[1] else None
            return (year_from, year_to)
        except Exception:
            return (None, None)
    text = str(value).strip()
    if not text:
        return (None, None)
    chunks = [item for item in text.replace("—", "-").replace("至", "-").split("-") if item.strip()]
    years: list[int] = []
    for chunk in chunks:
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if len(digits) >= 4:
            try:
                years.append(int(digits[:4]))
            except Exception:
                continue
    if not years:
        return (None, None)
    if len(years) == 1:
        return (years[0], years[0])
    return (years[0], years[-1])


def _infer_catalog_candidate_from_job(job: VehicleKnowledgeParseJob, pages: list[VehicleKnowledgeParsePage]) -> dict:
    raw = job.raw_result_json or {}
    summary = job.summary_json or {}
    normalized = raw.get("normalized_manual") or {}
    applicability = normalized.get("applicability") or {}
    document_profile = normalized.get("document_profile") or {}

    title = document_profile.get("document_title") or raw.get("title") or ""
    file_name = raw.get("file_name") or ""
    section_titles = " ".join(
        item.get("title") if isinstance(item, dict) else str(item)
        for item in (summary.get("sections") or [])
        if item
    )
    page_text = " ".join((page.text_content or "")[:2000] for page in pages[:5])
    combined_text = "\n".join([title, file_name, section_titles, page_text]).strip()

    brand = applicability.get("brand")
    model_name = applicability.get("model_name")
    if not model_name and combined_text:
        import re

        model_match = re.search(r"\b([A-Z]{2,}\d{2,}[A-Z0-9-]*)\b", combined_text)
        if model_match:
            model_name = model_match.group(1)

    year_from, year_to = _safe_year_range(applicability.get("year_range"))
    displacement_cc = None
    specs = summary.get("specs") or []
    for item in specs:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("type") or "").lower()
        value = item.get("value")
        unit = str(item.get("unit") or "").lower()
        if "排量" in label or "displacement" in label or unit == "cc":
            digits = "".join(ch for ch in str(value or "") if ch.isdigit())
            if digits:
                displacement_cc = int(digits)
                break
    if displacement_cc is None and combined_text:
        import re

        displacement_match = re.search(r"\b(\d{2,4})\s*cc\b", combined_text, re.I)
        if displacement_match:
            displacement_cc = int(displacement_match.group(1))

    if year_from is None:
        year_from = datetime.now().year
    if year_to is None:
        year_to = year_from

    return {
        "brand": (brand or "").strip().upper() or None,
        "model_name": (model_name or "").strip() or None,
        "year_from": year_from,
        "year_to": year_to,
        "year_range": f"{year_from}-{year_to}" if year_from and year_to else None,
        "displacement_cc": displacement_cc,
        "default_engine_code": applicability.get("engine_code"),
        "engine_code": applicability.get("engine_code"),
        "document_title": title or None,
        "source_pages": _ensure_list((normalized.get("traceability") or {}).get("source_pages")),
        "source_hint": combined_text[:4000],
    }


def _match_existing_catalog_model(db: Session, candidate: dict) -> Optional[VehicleCatalogModel]:
    brand_key = _normalize_match_text(candidate.get("brand"))
    model_key = _normalize_match_text(candidate.get("model_name"))
    if not brand_key or not model_key:
        return None
    rows = (
        db.query(VehicleCatalogModel)
        .filter(VehicleCatalogModel.is_active.is_(True))
        .all()
    )
    for row in rows:
        if _normalize_match_text(row.brand) == brand_key and _normalize_match_text(row.model_name) == model_key:
            return row
    return None


def _rebind_document_related_records(db: Session, document: VehicleKnowledgeDocument, target_model_id: int) -> None:
    db.query(VehicleKnowledgeParseJob).filter(
        VehicleKnowledgeParseJob.document_id == document.id
    ).update({"model_id": target_model_id}, synchronize_session=False)

    segments = db.query(VehicleKnowledgeSegment).filter(
        VehicleKnowledgeSegment.source_document_id == document.id
    ).all()
    vehicle_key = _catalog_vehicle_key(target_model_id)
    for segment in segments:
        segment.model_id = target_model_id
        if segment.segment_document_id:
            db.query(VehicleKnowledgeDocument).filter(
                VehicleKnowledgeDocument.id == segment.segment_document_id
            ).update({"model_id": target_model_id}, synchronize_session=False)
        if segment.procedure_id:
            db.query(Procedure).filter(Procedure.id == segment.procedure_id).update(
                {"vehicle_key": vehicle_key},
                synchronize_session=False,
            )


def _job_is_stale(job: VehicleKnowledgeParseJob, timeout_seconds: int = 600) -> bool:
    if not job or job.status not in {"queued", "processing"}:
        return False
    updated_at = job.updated_at or job.created_at
    if updated_at is None:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return age_seconds >= timeout_seconds


def _finalize_parse_job(job_id: int):
    db = SessionLocal()
    job = None
    try:
        job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
        if not job:
            return

        row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == job.document_id).first()
        if not row:
            job.status = "failed"
            job.error_message = "\u8d44\u6599\u4e0d\u5b58\u5728"
            job.progress_message = "\u8d44\u6599\u4e0d\u5b58\u5728"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        object_name = _resolve_object_name(row)
        if not object_name:
            job.status = "failed"
            job.error_message = "\u8be5\u8d44\u6599\u7f3a\u5c11\u5bf9\u8c61\u5b58\u50a8\u8def\u5f84\uff0c\u65e0\u6cd5\u53d1\u8d77\u89e3\u6790"
            job.progress_message = "\u8be5\u8d44\u6599\u7f3a\u5c11\u5bf9\u8c61\u5b58\u50a8\u8def\u5f84\uff0c\u65e0\u6cd5\u53d1\u8d77\u89e3\u6790"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.status = "processing"
        if not job.progress_percent:
            job.progress_percent = 1
        if not job.progress_message:
            job.progress_message = "\u5df2\u5f00\u59cb\u89e3\u6790\u8d44\u6599"
        db.commit()

        file_bytes = obj_storage.get_bytes(object_name)
        response = None
        last_error = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    f"{settings.AI_URL}/ai/ocr/parse",
                    files={
                        "file": (
                            row.file_name,
                            file_bytes,
                            row.file_type or "application/pdf",
                        )
                    },
                    data={
                        "document_id": str(row.id),
                        "model_id": str(row.model_id),
                        "title": row.title,
                        "category": row.category or "",
                        "job_id": str(job.id),
                    },
                    timeout=settings.OCR_REQUEST_TIMEOUT_SECONDS,
                )
                break
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("knowledge parse request attempt %s failed for job %s: %s", attempt, job.id, exc)
                if attempt >= 3:
                    raise
                db.refresh(job)
                job.status = "processing"
                job.progress_message = f"\u6b63\u5728\u91cd\u8bd5\u8fde\u63a5\u89e3\u6790\u670d\u52a1\uff08\u7b2c {attempt + 1} \u6b21\uff09"
                db.commit()
        if response is None and last_error:
            raise last_error

        response.raise_for_status()
        result = response.json()

        job.status = result.get("status") or "completed"
        job.provider = result.get("provider")
        job.parser_version = result.get("parser_version")
        job.page_count = result.get("page_count")
        job.extracted_sections = len(result.get("sections") or [])
        job.extracted_specs = len(result.get("specs") or [])
        job.processed_batches = result.get("processed_batches") or job.processed_batches
        job.total_batches = result.get("total_batches") or job.total_batches
        job.progress_percent = 100
        job.progress_message = "\u8d44\u6599\u89e3\u6790\u5b8c\u6210"
        job.summary_json = {
            "summary": result.get("summary"),
            "sections": result.get("sections") or [],
            "specs": result.get("specs") or [],
            "procedures": result.get("procedures") or [],
        }
        job.raw_result_json = result
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)

        db.query(VehicleKnowledgeParsePage).filter(
            VehicleKnowledgeParsePage.job_id == job.id
        ).delete(synchronize_session=False)

        for page in result.get("pages") or []:
            db.add(
                VehicleKnowledgeParsePage(
                    job_id=job.id,
                    document_id=row.id,
                    page_number=page.get("page_number") or 0,
                    page_label=page.get("page_label"),
                    text_content=page.get("text"),
                    summary=page.get("summary"),
                    blocks_json=page.get("blocks") or [],
                    specs_json=page.get("specs") or [],
                    procedures_json=page.get("procedures") or [],
                    confidence=page.get("confidence"),
                )
            )

        db.commit()
    except requests.HTTPError as exc:
        detail = "\u8d44\u6599\u89e3\u6790\u670d\u52a1\u8fd4\u56de\u5f02\u5e38"
        try:
            payload = exc.response.json()
            detail = payload.get("detail") or detail
        except Exception:
            pass
        logger.error(f"knowledge parse http error: {exc}")
        if job:
            job.status = "failed"
            job.error_message = detail
            job.progress_message = detail
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        logger.error(f"knowledge parse failed: {exc}", exc_info=True)
        if job:
            job.status = "failed"
            job.error_message = "\u8d44\u6599\u89e3\u6790\u5931\u8d25"
            job.progress_message = "\u8d44\u6599\u89e3\u6790\u5931\u8d25"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

@router.get("/vehicles", response_model=List[VehicleSchema])
async def list_vehicles(
    make: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    query = db.query(Vehicle)
    if make:
        query = query.filter(Vehicle.make == make)
    return query.all()

@router.get("/procedures", response_model=List[dict])
async def get_procedures(
    vehicle_model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Fetch procedures from Odoo for a specific vehicle model."""
    try:
        # Search drmoto.procedure where vehicle_id = vehicle_model_id
        domain = [['vehicle_id', '=', vehicle_model_id]]
        fields = ['id', 'name', 'description', 'total_cost']
        procedures = odoo_client.execute_kw('drmoto.procedure', 'search_read', [domain], {'fields': fields})
        return procedures
    except Exception as e:
        logger.error(f"Procedure fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch procedures from Odoo")


@router.get("/catalog-models/{model_id}/procedures", response_model=List[dict])
async def list_catalog_model_manuals(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    vehicle_key = _catalog_vehicle_key(model_id)
    procedures = (
        db.query(Procedure)
        .filter(Procedure.vehicle_key == vehicle_key)
        .order_by(Procedure.id.asc())
        .all()
    )
    result = []
    for proc in procedures:
        steps = (
            db.query(ProcedureStep)
            .filter(ProcedureStep.procedure_id == proc.id)
            .order_by(ProcedureStep.step_order.asc(), ProcedureStep.id.asc())
            .all()
        )
        result.append({
            "id": proc.id,
            "name": proc.name,
            "description": proc.description,
            "steps_count": len(steps),
            "steps": [
                {
                    "id": step.id,
                    "step_order": step.step_order,
                    "instruction": step.instruction,
                    "required_tools": step.required_tools,
                    "torque_spec": step.torque_spec,
                    "hazards": step.hazards,
                }
                for step in steps
            ],
        })
    return result


@router.post("/catalog-models/{model_id}/procedures", response_model=dict)
async def create_catalog_model_manual(
    model_id: int,
    payload: ManualProcedureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = Procedure(
        vehicle_key=_catalog_vehicle_key(model_id),
        name=payload.name,
        description=payload.description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "description": row.description, "steps_count": 0, "steps": []}


@router.put("/procedures/{procedure_id}", response_model=dict)
async def update_catalog_model_manual(
    procedure_id: int,
    payload: ManualProcedureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = db.query(Procedure).filter(Procedure.id == procedure_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Procedure not found")
    patch = payload.dict(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    for key, value in patch.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "description": row.description}


@router.delete("/procedures/{procedure_id}")
async def delete_catalog_model_manual(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = db.query(Procedure).filter(Procedure.id == procedure_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Procedure not found")
    db.query(ProcedureStep).filter(ProcedureStep.procedure_id == procedure_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": procedure_id}


@router.post("/procedures/{procedure_id}/steps", response_model=dict)
async def create_catalog_model_manual_step(
    procedure_id: int,
    payload: ManualStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    proc = db.query(Procedure).filter(Procedure.id == procedure_id).first()
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    row = ProcedureStep(
        procedure_id=procedure_id,
        step_order=payload.step_order,
        instruction=payload.instruction,
        required_tools=payload.required_tools,
        torque_spec=payload.torque_spec,
        hazards=payload.hazards,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "procedure_id": procedure_id,
        "step_order": row.step_order,
        "instruction": row.instruction,
        "required_tools": row.required_tools,
        "torque_spec": row.torque_spec,
        "hazards": row.hazards,
    }


@router.put("/procedures/{procedure_id}/steps/{step_id}", response_model=dict)
async def update_catalog_model_manual_step(
    procedure_id: int,
    step_id: int,
    payload: ManualStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = (
        db.query(ProcedureStep)
        .filter(ProcedureStep.id == step_id, ProcedureStep.procedure_id == procedure_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Procedure step not found")
    patch = payload.dict(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    for key, value in patch.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "procedure_id": procedure_id,
        "step_order": row.step_order,
        "instruction": row.instruction,
        "required_tools": row.required_tools,
        "torque_spec": row.torque_spec,
        "hazards": row.hazards,
    }


@router.delete("/procedures/{procedure_id}/steps/{step_id}")
async def delete_catalog_model_manual_step(
    procedure_id: int,
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = (
        db.query(ProcedureStep)
        .filter(ProcedureStep.id == step_id, ProcedureStep.procedure_id == procedure_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Procedure step not found")
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": step_id}


@router.get("/catalog-models/{model_id}/documents", response_model=List[KnowledgeDocumentResponse])
async def list_catalog_model_documents(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    rows = (
        db.query(VehicleKnowledgeDocument)
        .filter(VehicleKnowledgeDocument.model_id == model_id)
        .order_by(VehicleKnowledgeDocument.created_at.desc(), VehicleKnowledgeDocument.id.desc())
        .all()
    )
    latest_jobs = _latest_jobs_map(db, [row.id for row in rows])
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    confirmed_ids = sorted({row.catalog_confirmed_model_id for row in rows if row.catalog_confirmed_model_id})
    confirmed_map = {
        row.id: row
        for row in db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id.in_(confirmed_ids or [-1])).all()
    }
    results = []
    for row in rows:
        latest_job = latest_jobs.get(row.id)
        _apply_catalog_candidate_snapshot(row, latest_job)
        results.append(_document_to_dict(row, latest_job, model, confirmed_map.get(row.catalog_confirmed_model_id)))
    db.commit()
    return results


@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
async def list_all_knowledge_documents(
    keyword: str = "",
    category: str = "",
    parse_status: str = "",
    review_status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    rows = (
        db.query(VehicleKnowledgeDocument)
        .order_by(VehicleKnowledgeDocument.created_at.desc(), VehicleKnowledgeDocument.id.desc())
        .all()
    )
    latest_jobs = _latest_jobs_map(db, [row.id for row in rows])
    row_map = {row.id: row for row in rows}
    model_ids = sorted({row.model_id for row in rows if row.model_id})
    model_map = {
        row.id: row
        for row in db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id.in_(model_ids or [-1])).all()
    }
    confirmed_ids = sorted({row.catalog_confirmed_model_id for row in rows if row.catalog_confirmed_model_id})
    confirmed_map = {
        row.id: row
        for row in db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id.in_(confirmed_ids or [-1])).all()
    }

    keyword_key = _normalize_match_text(keyword)
    category_key = _normalize_match_text(category)
    parse_status_key = _normalize_match_text(parse_status)
    review_status_key = _normalize_match_text(review_status)
    filtered: list[dict] = []
    for row in rows:
        latest_job = latest_jobs.get(row.id)
        model = model_map.get(row.model_id)
        _apply_catalog_candidate_snapshot(row, latest_job)
        payload = _document_to_dict(row, latest_job, model, confirmed_map.get(row.catalog_confirmed_model_id))
        if keyword_key:
            haystack = _normalize_match_text(
                " ".join(
                    [
                        row.title or "",
                        row.file_name or "",
                        row.notes or "",
                        model.brand if model else "",
                        model.model_name if model else "",
                    ]
                )
            )
            if keyword_key not in haystack:
                continue
        if category_key and _normalize_match_text(row.category) != category_key:
            continue
        if parse_status_key and _normalize_match_text(latest_job.status if latest_job else "pending") != parse_status_key:
            continue
        if review_status_key and _normalize_match_text(row.review_status or "pending_review") != review_status_key:
            continue
        filtered.append(payload)
    if keyword_key:
        filtered.sort(
            key=lambda item: _document_search_rank(
                item,
                row_map.get(item["id"]),
                latest_jobs.get(item["id"]),
                model_map.get(item.get("model_id")),
                keyword,
            ),
            reverse=True,
        )
    db.commit()
    return filtered


@router.patch("/documents/{document_id}/review", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document_review(
    document_id: int,
    payload: KnowledgeDocumentReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")
    review_status = (payload.review_status or "").strip()
    if review_status not in {"pending_review", "confirmed", "needs_fix"}:
        raise HTTPException(status_code=400, detail="无效的审核状态")
    row.review_status = review_status
    row.review_notes = (payload.review_notes or "").strip() or None
    row.reviewed_by = current_user.username
    row.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == row.model_id).first()
    confirmed_model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == row.catalog_confirmed_model_id).first() if row.catalog_confirmed_model_id else None
    latest_job = (
        db.query(VehicleKnowledgeParseJob)
        .filter(VehicleKnowledgeParseJob.document_id == row.id)
        .order_by(VehicleKnowledgeParseJob.id.desc())
        .first()
    )
    _apply_catalog_candidate_snapshot(row, latest_job)
    db.commit()
    return _document_to_dict(row, latest_job, model, confirmed_model)


@router.patch("/documents/{document_id}/catalog-confirmation", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document_catalog_confirmation(
    document_id: int,
    payload: KnowledgeDocumentCatalogConfirmationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")

    latest_job = (
        db.query(VehicleKnowledgeParseJob)
        .filter(VehicleKnowledgeParseJob.document_id == row.id)
        .order_by(VehicleKnowledgeParseJob.id.desc())
        .first()
    )
    pages = []
    if latest_job:
        pages = (
            db.query(VehicleKnowledgeParsePage)
            .filter(VehicleKnowledgeParsePage.job_id == latest_job.id)
            .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
            .all()
        )
    candidate = _apply_catalog_candidate_snapshot(row, latest_job, pages)
    action = (payload.action or "").strip()
    if action not in {"confirm_current", "bind_existing", "create_new", "reset_pending"}:
        raise HTTPException(status_code=400, detail="无效的车型确认动作")

    if action == "reset_pending":
        row.catalog_confirmation_status = "pending_confirmation"
        row.catalog_confirmed_model_id = None
        row.catalog_confirmed_by = None
        row.catalog_confirmed_at = None
        db.commit()
        db.refresh(row)
        model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == row.model_id).first()
        return _document_to_dict(row, latest_job, model, None)

    target_model: Optional[VehicleCatalogModel] = None
    created = False
    if action == "confirm_current":
        target_model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == row.model_id).first()
        if not target_model:
            raise HTTPException(status_code=404, detail="当前资料绑定的车型不存在")
    elif action == "bind_existing":
        model_id = int(payload.model_id or 0)
        if not model_id:
            raise HTTPException(status_code=400, detail="请选择要绑定的标准车型")
        target_model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
        if not target_model:
            raise HTTPException(status_code=404, detail="目标标准车型不存在")
    else:
        brand = (payload.brand or candidate.get("brand") or "").strip()
        model_name = (payload.model_name or candidate.get("model_name") or "").strip()
        if not brand or not model_name:
            raise HTTPException(status_code=400, detail="请先补全品牌和车型，再新建标准车型")
        year_from = int(payload.year_from or candidate.get("year_from") or datetime.now().year)
        year_to = _normalize_year_to(year_from, int(payload.year_to or candidate.get("year_to") or year_from))
        target_model = VehicleCatalogModel(
            brand=brand,
            model_name=model_name,
            year_from=year_from,
            year_to=year_to,
            displacement_cc=payload.displacement_cc if payload.displacement_cc is not None else candidate.get("displacement_cc"),
            category=(payload.category or "街车/跑车").strip() or "街车/跑车",
            fuel_type="gasoline",
            default_engine_code=(payload.default_engine_code or candidate.get("default_engine_code") or None),
            source="ocr_manual_confirmed",
            is_active=True,
        )
        db.add(target_model)
        db.flush()
        _ensure_baseline_service_items_for_model(db, target_model.id)
        created = True

    row.catalog_candidate_json = candidate or None
    _set_document_catalog_confirmation(row, target_model, current_user)
    _rebind_document_related_records(db, row, target_model.id)
    if payload.notes is not None:
        row.review_notes = (payload.notes or "").strip() or row.review_notes
    db.commit()
    db.refresh(row)

    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == row.model_id).first()
    response = _document_to_dict(row, latest_job, model, target_model)
    response["catalog_confirmation_created"] = created
    return response


@router.post("/catalog-models/{model_id}/documents", response_model=KnowledgeDocumentResponse)
async def upload_catalog_model_document(
    model_id: int,
    title: str = Form(""),
    category: str = Form("维修手册"),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if model is None:
        raise HTTPException(status_code=404, detail="车型不存在")

    safe_title = _validate_bounded_text(title, "title", KNOWLEDGE_TITLE_MAX)
    safe_category = _validate_bounded_text(category, "category", KNOWLEDGE_CATEGORY_MAX, default="维修手册")
    safe_notes = _validate_bounded_text(notes, "notes", KNOWLEDGE_NOTES_MAX)
    filename = normalize_text(file.filename) or ""
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 手册")
    content_type = normalize_text(file.content_type) or "application/pdf"
    if content_type and "pdf" not in content_type.lower():
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 手册")

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="上传文件不能为空")
        if len(contents) > KNOWLEDGE_UPLOAD_MAX_BYTES:
            raise HTTPException(status_code=400, detail="PDF 文件过大，请控制在 120MB 以内")
        object_name = build_storage_object_name(f"knowledge/catalog-models/{model_id}", filename)
        file_url = obj_storage.put_bytes(object_name, contents, content_type)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"knowledge document upload failed: {exc}")
        raise HTTPException(status_code=500, detail="资料上传失败")

    row = VehicleKnowledgeDocument(
        model_id=model_id,
        title=safe_title or filename,
        file_name=filename,
        object_name=object_name,
        file_url=file_url,
        file_type=content_type,
        category=safe_category or "维修手册",
        notes=safe_notes,
        catalog_confirmation_status="pending_confirmation",
        uploaded_by=current_user.username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _document_to_dict(row, None, model, None)


@router.delete("/documents/{document_id}")
async def delete_catalog_model_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")
    db.query(VehicleKnowledgeParsePage).filter(VehicleKnowledgeParsePage.document_id == document_id).delete(synchronize_session=False)
    db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.document_id == document_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    object_name = _resolve_object_name(row)
    if object_name:
        try:
            obj_storage.remove(object_name)
        except Exception as exc:
            logger.warning(f"knowledge document object remove failed: {exc}")
    return {"deleted": 1, "id": document_id}


@router.get("/documents/{document_id}/download")
async def download_catalog_model_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")
    object_name = _resolve_object_name(row)
    if not object_name:
        raise HTTPException(status_code=400, detail="该资料缺少对象存储路径")
    try:
        file_bytes = obj_storage.get_bytes(object_name)
    except Exception as exc:
        logger.error(f"knowledge document download failed: {exc}")
        raise HTTPException(status_code=500, detail="资料读取失败")
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{requests.utils.quote(row.file_name)}"
    }
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=row.file_type or "application/octet-stream",
        headers=headers,
    )


@router.post("/documents/{document_id}/parse", response_model=KnowledgeParseJobResponse)
async def parse_catalog_model_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")
    object_name = _resolve_object_name(row)
    if not object_name:
        raise HTTPException(status_code=400, detail="该资料缺少对象存储路径，无法发起解析")
    if row.object_name != object_name:
        row.object_name = object_name
        db.commit()
        db.refresh(row)

    existing_job = (
        db.query(VehicleKnowledgeParseJob)
        .filter(
            VehicleKnowledgeParseJob.document_id == row.id,
            VehicleKnowledgeParseJob.status.in_(["queued", "processing"]),
        )
        .order_by(VehicleKnowledgeParseJob.id.desc())
        .first()
    )
    if existing_job:
        if _job_is_stale(existing_job):
            existing_job.status = "failed"
            existing_job.error_message = "\u65e7\u7684\u89e3\u6790\u4efb\u52a1\u957f\u65f6\u95f4\u672a\u66f4\u65b0\uff0c\u7cfb\u7edf\u5df2\u81ea\u52a8\u91cd\u542f"
            existing_job.progress_message = "\u65e7\u7684\u89e3\u6790\u4efb\u52a1\u5df2\u6807\u8bb0\u4e3a\u8d85\u65f6"
            existing_job.completed_at = datetime.now(timezone.utc)
            db.commit()
        else:
            return _job_to_dict(existing_job)

    job = VehicleKnowledgeParseJob(
        document_id=row.id,
        model_id=row.model_id,
        status="queued",
        triggered_by=current_user.username,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_finalize_parse_job, job.id)
    return _job_to_dict(job)


@router.post("/parse-jobs/{job_id}/retry", response_model=KnowledgeParseJobResponse)
async def retry_catalog_model_document_parse_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    source_job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not source_job:
        raise HTTPException(status_code=404, detail="解析任务不存在")

    row = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == source_job.document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="资料不存在")

    running_job = (
        db.query(VehicleKnowledgeParseJob)
        .filter(
            VehicleKnowledgeParseJob.document_id == row.id,
            VehicleKnowledgeParseJob.status.in_(["queued", "processing"]),
            VehicleKnowledgeParseJob.id != source_job.id,
        )
        .order_by(VehicleKnowledgeParseJob.id.desc())
        .first()
    )
    if running_job and not _job_is_stale(running_job):
        return _job_to_dict(running_job)
    if running_job and _job_is_stale(running_job):
        running_job.status = "failed"
        running_job.error_message = "\u89e3\u6790\u4efb\u52a1\u8d85\u65f6\uff0c\u5df2\u7531\u91cd\u8bd5\u4efb\u52a1\u63a5\u7ba1"
        running_job.progress_message = "\u89e3\u6790\u4efb\u52a1\u8d85\u65f6"
        running_job.completed_at = datetime.now(timezone.utc)
        db.commit()

    retry_job = VehicleKnowledgeParseJob(
        document_id=row.id,
        model_id=row.model_id,
        status="queued",
        triggered_by=current_user.username,
        progress_message="\u6b63\u5728\u91cd\u65b0\u53d1\u8d77\u89e3\u6790",
    )
    db.add(retry_job)
    db.commit()
    db.refresh(retry_job)
    background_tasks.add_task(_finalize_parse_job, retry_job.id)
    return _job_to_dict(retry_job)


@router.post("/parse-jobs/{job_id}/resume", response_model=KnowledgeParseJobResponse)
async def resume_catalog_model_document_parse_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    row = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="解析任务不存在")

    if row.status == "completed" and row.summary_json and row.raw_result_json:
        return _job_to_dict(row)

    if row.status == "failed":
        raise HTTPException(status_code=400, detail="当前任务已失败，请使用重试")

    pages_count = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == row.id)
        .count()
    )
    is_stale = _job_is_stale(row, timeout_seconds=300)
    appears_incomplete = not row.summary_json or not row.raw_result_json or pages_count == 0
    if not is_stale and row.status in {"queued", "processing"} and not appears_incomplete:
        return _job_to_dict(row)

    row.status = "queued"
    row.progress_message = "正在恢复解析收尾任务"
    row.error_message = None
    row.completed_at = None
    if not row.progress_percent or row.progress_percent < 95:
        row.progress_percent = 95
    db.commit()
    db.refresh(row)
    background_tasks.add_task(_finalize_parse_job, row.id)
    return _job_to_dict(row)


@router.post("/internal/parse-jobs/{job_id}/progress", include_in_schema=False)
async def update_parse_job_progress(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    row = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="解析任务不存在")

    try:
        if "status" in payload and payload["status"]:
            row.status = str(payload["status"])
        if "processed_batches" in payload and payload["processed_batches"] is not None:
            row.processed_batches = int(payload["processed_batches"])
        if "total_batches" in payload and payload["total_batches"] is not None:
            row.total_batches = int(payload["total_batches"])
        if "progress_percent" in payload and payload["progress_percent"] is not None:
            row.progress_percent = max(0, min(100, int(payload["progress_percent"])))
        if "progress_message" in payload:
            row.progress_message = _validate_bounded_text(payload["progress_message"], "progress_message", 500)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="解析任务进度参数格式不正确") from exc
    db.commit()
    db.refresh(row)
    return _job_to_dict(row)


@router.get("/documents/{document_id}/parse-jobs", response_model=List[KnowledgeParseJobResponse])
async def list_catalog_model_document_parse_jobs(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    rows = (
        db.query(VehicleKnowledgeParseJob)
        .filter(VehicleKnowledgeParseJob.document_id == document_id)
        .order_by(VehicleKnowledgeParseJob.id.desc())
        .all()
    )
    return [_job_to_dict(row) for row in rows]


@router.get("/parse-jobs/{job_id}", response_model=KnowledgeParseJobDetailResponse)
async def get_catalog_model_document_parse_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    row = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    payload = _job_to_dict(row)
    payload["pages"] = [_page_to_dict(page) for page in pages]
    return payload


@router.patch("/parse-jobs/{job_id}/result", response_model=KnowledgeParseJobDetailResponse)
async def update_catalog_model_document_parse_job_result(
    job_id: int,
    payload: KnowledgeParseJobResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    row = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    raw = _ensure_dict(row.raw_result_json)
    summary = _ensure_dict(row.summary_json)
    normalized = _ensure_dict(raw.get("normalized_manual"))
    applicability = _ensure_dict(normalized.get("applicability"))
    traceability = _ensure_dict(normalized.get("traceability"))

    if payload.applicability is not None:
        applicability.update(_ensure_dict(payload.applicability))
        source_pages = applicability.pop("source_pages", None)
        if source_pages is not None:
            traceability["source_pages"] = _ensure_list(source_pages)
        normalized["applicability"] = applicability
        normalized["traceability"] = traceability
    if payload.sections is not None:
        summary["sections"] = _ensure_list(payload.sections)
    if payload.specs is not None:
        summary["specs"] = _ensure_list(payload.specs)
    if payload.procedures is not None:
        summary["procedures"] = _ensure_list(payload.procedures)
        procedures_block = _ensure_dict(normalized.get("procedures"))
        procedures_block["steps"] = _ensure_list(payload.procedures)
        normalized["procedures"] = procedures_block
    if payload.review_notes is not None:
        raw["editor_notes"] = (payload.review_notes or "").strip() or None

    raw["normalized_manual"] = normalized
    row.summary_json = summary
    row.raw_result_json = raw
    row.updated_at = datetime.now(timezone.utc)
    row.progress_message = "识别结果已人工修订"
    row.extracted_sections = len(_ensure_list(summary.get("sections")))
    row.extracted_specs = len(_ensure_list(summary.get("specs")))
    db.commit()
    db.refresh(row)

    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    result = _job_to_dict(row)
    result["pages"] = [_page_to_dict(page) for page in pages]
    return result


@router.patch("/parse-pages/{page_id}", response_model=KnowledgeParseJobDetailResponse)
async def update_catalog_model_document_parse_page(
    page_id: int,
    payload: KnowledgeParsePageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    page = db.query(VehicleKnowledgeParsePage).filter(VehicleKnowledgeParsePage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="解析页面不存在")
    if payload.summary is not None:
        page.summary = (payload.summary or "").strip() or None
    if payload.text_content is not None:
        page.text_content = payload.text_content
    if payload.specs_json is not None:
        page.specs_json = _ensure_list(payload.specs_json)
    if payload.procedures_json is not None:
        page.procedures_json = _ensure_list(payload.procedures_json)

    job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == page.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == page.job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    _recalculate_job_summary(job, pages)
    job.updated_at = datetime.now(timezone.utc)
    job.progress_message = f"第 {page.page_number} 页已人工修订"
    db.commit()
    db.refresh(job)
    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == page.job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    result = _job_to_dict(job)
    result["pages"] = [_page_to_dict(item) for item in pages]
    return result


@router.post("/parse-jobs/{job_id}/bind-catalog-model")
async def bind_parse_job_to_catalog_model(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="解析任务不存在")

    document = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == job.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")

    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    candidate = _infer_catalog_candidate_from_job(job, pages)
    if not candidate.get("brand") or not candidate.get("model_name"):
        raise HTTPException(status_code=400, detail="当前解析结果还无法识别出稳定的品牌和车型")

    target_model = _match_existing_catalog_model(db, candidate)
    created = False
    if not target_model:
        target_model = VehicleCatalogModel(
            brand=candidate["brand"],
            model_name=candidate["model_name"],
            year_from=int(candidate["year_from"]),
            year_to=_normalize_year_to(int(candidate["year_from"]), int(candidate["year_to"])),
            displacement_cc=candidate.get("displacement_cc"),
            category="街车/跑车",
            fuel_type="gasoline",
            default_engine_code=candidate.get("default_engine_code"),
            source="ocr_manual_import",
            is_active=True,
        )
        db.add(target_model)
        db.flush()
        _ensure_baseline_service_items_for_model(db, target_model.id)
        created = True

    document.catalog_candidate_json = candidate or None
    _set_document_catalog_confirmation(document, target_model, current_user)
    _rebind_document_related_records(db, document, target_model.id)
    db.commit()
    db.refresh(target_model)

    return {
        "created": created,
        "model": {
            "id": target_model.id,
            "brand": target_model.brand,
            "model_name": target_model.model_name,
            "year_from": target_model.year_from,
            "year_to": target_model.year_to,
            "displacement_cc": target_model.displacement_cc,
            "category": target_model.category,
            "fuel_type": target_model.fuel_type,
            "default_engine_code": target_model.default_engine_code,
            "source": target_model.source,
        },
        "document_id": document.id,
        "job_id": job.id,
        "recognized": candidate,
    }


@router.post("/parse-jobs/{job_id}/import-confirmed-specs")
async def import_confirmed_specs_to_catalog_model(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    document = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == job.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")
    _require_catalog_confirmation(document)
    model_id = int(job.model_id or 0)
    if not model_id:
        raise HTTPException(status_code=400, detail="请先将资料绑定到标准车型，再导入规格")
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="标准车型不存在")

    summary = _ensure_dict(job.summary_json)
    specs = _preferred_specs([item for item in _ensure_list(summary.get("specs")) if isinstance(item, dict)])
    confirmed_specs = [item for item in specs if item.get("review_status") == "confirmed"]
    import_rows = confirmed_specs or specs
    if not import_rows:
        raise HTTPException(status_code=400, detail="当前没有可导入的规格候选")

    imported = 0
    for item in import_rows:
        source_page = None if item.get("page_number") is None else str(item.get("page_number"))
        spec_key = _normalize_spec_key(item.get("label"), item.get("type"))
        row = (
            db.query(VehicleCatalogSpec)
            .filter(
                VehicleCatalogSpec.model_id == model_id,
                VehicleCatalogSpec.spec_key == spec_key,
                VehicleCatalogSpec.source_page == source_page,
            )
            .first()
        )
        if not row:
            row = VehicleCatalogSpec(
                model_id=model_id,
                spec_key=spec_key,
                spec_label=item.get("label") or spec_key,
            )
            db.add(row)
        row.spec_label = item.get("label") or row.spec_label or spec_key
        row.spec_type = item.get("type")
        row.spec_value = None if item.get("value") is None else str(item.get("value"))
        row.spec_unit = item.get("unit")
        row.source_page = source_page
        row.source_text = item.get("source_text")
        row.review_status = item.get("review_status") or "confirmed"
        row.source = "ocr_manual"
        imported += 1
    db.commit()
    return {"imported": imported, "model_id": model_id}


@router.get("/catalog-models/{model_id}/segments", response_model=List[KnowledgeSegmentResponse])
async def list_catalog_model_segments(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    rows = (
        db.query(VehicleKnowledgeSegment)
        .filter(VehicleKnowledgeSegment.model_id == model_id)
        .order_by(VehicleKnowledgeSegment.chapter_no.asc().nullslast(), VehicleKnowledgeSegment.start_page.asc().nullslast(), VehicleKnowledgeSegment.id.asc())
        .all()
    )
    document_ids = [row.segment_document_id for row in rows if row.segment_document_id]
    procedure_ids = [row.procedure_id for row in rows if row.procedure_id]
    documents = {}
    if document_ids:
        for item in db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id.in_(document_ids)).all():
            documents[item.id] = item
    procedures = {}
    if procedure_ids:
        for item in db.query(Procedure).filter(Procedure.id.in_(procedure_ids)).all():
            procedures[item.id] = item
    steps_map: dict[int, list[ProcedureStep]] = {}
    if procedure_ids:
        for step in (
            db.query(ProcedureStep)
            .filter(ProcedureStep.procedure_id.in_(procedure_ids))
            .order_by(ProcedureStep.procedure_id.asc(), ProcedureStep.step_order.asc(), ProcedureStep.id.asc())
            .all()
        ):
            steps_map.setdefault(step.procedure_id, []).append(step)
    return [
        _segment_to_dict(
            row,
            segment_document=documents.get(row.segment_document_id),
            procedure=procedures.get(row.procedure_id),
            steps=steps_map.get(row.procedure_id, []),
        )
        for row in rows
    ]


@router.post("/parse-jobs/{job_id}/materialize-segments")
async def materialize_parse_job_segments(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    job = db.query(VehicleKnowledgeParseJob).filter(VehicleKnowledgeParseJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    source_document = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == job.document_id).first()
    if not source_document:
        raise HTTPException(status_code=404, detail="源资料不存在")
    _require_catalog_confirmation(source_document)
    if not source_document.model_id:
        raise HTTPException(status_code=400, detail="源资料未绑定车型")
    object_name = _resolve_object_name(source_document)
    if not object_name:
        raise HTTPException(status_code=400, detail="源资料缺少对象存储路径")
    try:
        source_bytes = obj_storage.get_bytes(object_name)
    except Exception as exc:
        logger.error(f"knowledge segment source read failed: {exc}")
        raise HTTPException(status_code=500, detail="读取源资料失败")
    reader = PdfReader(io.BytesIO(source_bytes))
    raw = _ensure_dict(job.raw_result_json)
    normalized = _ensure_dict(raw.get("normalized_manual"))
    toc_segments = _ensure_list(normalized.get("toc_segments"))
    segment_source = "ocr_toc"
    if not toc_segments:
        toc_segments = _build_segments_from_pdf_outline(reader)
        segment_source = "pdf_outline"
    if not toc_segments:
        raise HTTPException(status_code=400, detail="当前解析结果尚未形成目录分段")
    pages = (
        db.query(VehicleKnowledgeParsePage)
        .filter(VehicleKnowledgeParsePage.job_id == job_id)
        .order_by(VehicleKnowledgeParsePage.page_number.asc(), VehicleKnowledgeParsePage.id.asc())
        .all()
    )
    vehicle_key = _catalog_vehicle_key(source_document.model_id)
    materialized = []
    for segment in toc_segments:
        title = str(segment.get("title") or "").strip()
        start_page = segment.get("start_page")
        if not title or not start_page:
            continue
        try:
            start_page = int(start_page)
        except Exception:
            continue
        end_page = segment.get("end_page")
        try:
            end_page = int(end_page) if end_page else start_page
        except Exception:
            end_page = start_page
        end_page = max(start_page, min(end_page or start_page, len(reader.pages)))
        writer = PdfWriter()
        for page_index in range(start_page - 1, end_page):
            if 0 <= page_index < len(reader.pages):
                writer.add_page(reader.pages[page_index])
        if not writer.pages:
            continue
        buffer = io.BytesIO()
        writer.write(buffer)
        chapter_no = str(segment.get("chapter_no") or "").strip() or None
        file_name = _segment_file_name(chapter_no, title, source_document.file_name)
        object_name = build_storage_object_name(f"knowledge/catalog-models/{source_document.model_id}/segments", file_name)
        file_url = obj_storage.put_bytes(object_name, buffer.getvalue(), source_document.file_type or "application/pdf")

        existing = (
            db.query(VehicleKnowledgeSegment)
            .filter(
                VehicleKnowledgeSegment.source_job_id == job_id,
                VehicleKnowledgeSegment.title == title,
                VehicleKnowledgeSegment.start_page == start_page,
            )
            .first()
        )
        segment_document = None
        if existing and existing.segment_document_id:
            segment_document = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.id == existing.segment_document_id).first()
        if not segment_document:
            segment_document = VehicleKnowledgeDocument(
                model_id=source_document.model_id,
                title=title,
                file_name=file_name,
                object_name=object_name,
                file_url=file_url,
                file_type=source_document.file_type or "application/pdf",
                category="维修手册分段",
                notes=f"来源资料#{source_document.id}，页码 {start_page}-{end_page}",
                review_status="pending_review",
                uploaded_by=current_user.username,
            )
            db.add(segment_document)
            db.flush()
        else:
            segment_document.title = title
            segment_document.file_name = file_name
            segment_document.object_name = object_name
            segment_document.file_url = file_url
            segment_document.file_type = source_document.file_type or "application/pdf"
            segment_document.category = "维修手册分段"
            segment_document.notes = f"来源资料#{source_document.id}，页码 {start_page}-{end_page}"

        proc = None
        if existing and existing.procedure_id:
            proc = db.query(Procedure).filter(Procedure.id == existing.procedure_id).first()
        if proc and existing and existing.id:
            reused_elsewhere = (
                db.query(VehicleKnowledgeSegment)
                .filter(
                    VehicleKnowledgeSegment.procedure_id == proc.id,
                    VehicleKnowledgeSegment.id != existing.id,
                )
                .first()
            )
            if reused_elsewhere:
                proc = None
        if not proc:
            proc = Procedure(vehicle_key=vehicle_key, name=title, description=f"章节页码：{start_page}-{end_page}")
            db.add(proc)
            db.flush()
        else:
            proc.description = f"章节页码：{start_page}-{end_page}"

        db.query(ProcedureStep).filter(ProcedureStep.procedure_id == proc.id).delete(synchronize_session=False)
        extracted_steps = _extract_steps_from_page_range(pages, start_page, end_page)
        if len(extracted_steps) < 2:
            text_steps = _extract_steps_from_segment_text(reader, start_page, end_page, title)
            if len(text_steps) > len(extracted_steps):
                extracted_steps = text_steps
        if not extracted_steps:
            extracted_steps = _extract_steps_from_outline_segment(segment, start_page, end_page)
        if len(extracted_steps) <= 1:
            extracted_steps = _build_semantic_fallback_steps(title, start_page, end_page)
        for step in extracted_steps:
            db.add(
                ProcedureStep(
                    procedure_id=proc.id,
                    step_order=int(step.get("step_order") or 1),
                    instruction=str(step.get("instruction") or ""),
                    required_tools=step.get("required_tools"),
                    torque_spec=step.get("torque_spec"),
                    hazards=step.get("hazards"),
                )
            )

        if not existing:
            existing = VehicleKnowledgeSegment(
                model_id=source_document.model_id,
                source_document_id=source_document.id,
                source_job_id=job_id,
                chapter_no=chapter_no,
                title=title,
                start_page=start_page,
                end_page=end_page,
                review_status="pending_review",
            )
            db.add(existing)
        existing.chapter_no = chapter_no
        existing.title = title
        existing.start_page = start_page
        existing.end_page = end_page
        existing.segment_document_id = segment_document.id
        existing.procedure_id = proc.id
        existing.notes = f"来源资料#{source_document.id} / 目录页 {segment.get('toc_page_number') or '-'} / {segment_source}"
        materialized.append(existing)

    db.commit()
    return {"materialized": len(materialized), "model_id": source_document.model_id, "job_id": job_id, "source": segment_source}

@router.post("/seed")
async def seed_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """
    Seeds the database with a Comprehensive Framework of International and Domestic Motorcycles (2015-2025).
    """
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Endpoint disabled")

    motorcycles = [
        # ==================== KAWASAKI (川崎) ====================
        {"key": "KAWASAKI|NINJA400|2018|399", "make": "Kawasaki", "model": "Ninja 400", "year_from": 2018, "engine_code": "399cc Twin"},
        {"key": "KAWASAKI|NINJA250|2018|249", "make": "Kawasaki", "model": "Ninja 250", "year_from": 2018, "engine_code": "249cc Twin"},
        {"key": "KAWASAKI|NINJA500|2024|451", "make": "Kawasaki", "model": "Ninja 500", "year_from": 2024, "engine_code": "451cc Twin"},
        {"key": "KAWASAKI|NINJA650|2017|649", "make": "Kawasaki", "model": "Ninja 650", "year_from": 2017, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|ZX6R|2019|636", "make": "Kawasaki", "model": "Ninja ZX-6R", "year_from": 2019, "engine_code": "636cc Inline-4"},
        {"key": "KAWASAKI|ZX10R|2021|998", "make": "Kawasaki", "model": "Ninja ZX-10R", "year_from": 2021, "engine_code": "998cc Inline-4"},
        {"key": "KAWASAKI|Z400|2019|399", "make": "Kawasaki", "model": "Z400", "year_from": 2019, "engine_code": "399cc Twin"},
        {"key": "KAWASAKI|Z650|2017|649", "make": "Kawasaki", "model": "Z650", "year_from": 2017, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|Z900|2017|948", "make": "Kawasaki", "model": "Z900", "year_from": 2017, "engine_code": "948cc Inline-4"},
        {"key": "KAWASAKI|Z900RS|2018|948", "make": "Kawasaki", "model": "Z900RS", "year_from": 2018, "engine_code": "948cc Inline-4"},
        {"key": "KAWASAKI|VERSYS650|2015|649", "make": "Kawasaki", "model": "Versys 650", "year_from": 2015, "engine_code": "649cc Twin"},
        {"key": "KAWASAKI|VULCANS|2015|649", "make": "Kawasaki", "model": "Vulcan S", "year_from": 2015, "engine_code": "649cc Twin"},

        # ==================== HONDA (本田) ====================
        {"key": "HONDA|CBR650R|2019|649", "make": "Honda", "model": "CBR650R", "year_from": 2019, "engine_code": "649cc Inline-4"},
        {"key": "HONDA|CB650R|2019|649", "make": "Honda", "model": "CB650R", "year_from": 2019, "engine_code": "649cc Inline-4"},
        {"key": "HONDA|CBR500R|2019|471", "make": "Honda", "model": "CBR500R", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CB500F|2019|471", "make": "Honda", "model": "CB500F", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CB500X|2019|471", "make": "Honda", "model": "CB500X", "year_from": 2019, "engine_code": "471cc Twin"},
        {"key": "HONDA|CM300|2020|286", "make": "Honda", "model": "CM300 (Rebel 300)", "year_from": 2020, "engine_code": "286cc Single"},
        {"key": "HONDA|CM500|2017|471", "make": "Honda", "model": "CM500 (Rebel 500)", "year_from": 2017, "engine_code": "471cc Twin"},
        {"key": "HONDA|CM1100|2021|1084", "make": "Honda", "model": "CM1100 (Rebel 1100)", "year_from": 2021, "engine_code": "1084cc Twin"},
        {"key": "HONDA|CBR1000RR|2020|1000", "make": "Honda", "model": "CBR1000RR-R", "year_from": 2020, "engine_code": "1000cc Inline-4"},
        {"key": "HONDA|CRF1100L|2020|1084", "make": "Honda", "model": "Africa Twin CRF1100L", "year_from": 2020, "engine_code": "1084cc Twin"},
        {"key": "HONDA|GL1800|2018|1833", "make": "Honda", "model": "Gold Wing GL1800", "year_from": 2018, "engine_code": "1833cc Flat-6"},
        {"key": "HONDA|XADV750|2021|745", "make": "Honda", "model": "X-ADV 750", "year_from": 2021, "engine_code": "745cc Twin"},

        # ==================== YAMAHA (雅马哈) ====================
        {"key": "YAMAHA|R3|2019|321", "make": "Yamaha", "model": "YZF-R3", "year_from": 2019, "engine_code": "321cc Twin"},
        {"key": "YAMAHA|R7|2021|689", "make": "Yamaha", "model": "YZF-R7", "year_from": 2021, "engine_code": "689cc Twin"},
        {"key": "YAMAHA|R1|2020|998", "make": "Yamaha", "model": "YZF-R1", "year_from": 2020, "engine_code": "998cc Inline-4"},
        {"key": "YAMAHA|MT03|2020|321", "make": "Yamaha", "model": "MT-03", "year_from": 2020, "engine_code": "321cc Twin"},
        {"key": "YAMAHA|MT07|2021|689", "make": "Yamaha", "model": "MT-07", "year_from": 2021, "engine_code": "689cc Twin"},
        {"key": "YAMAHA|MT09|2021|890", "make": "Yamaha", "model": "MT-09", "year_from": 2021, "engine_code": "890cc Triple"},
        {"key": "YAMAHA|XMAX300|2018|292", "make": "Yamaha", "model": "XMAX 300", "year_from": 2018, "engine_code": "292cc Single"},
        {"key": "YAMAHA|TMAX560|2020|562", "make": "Yamaha", "model": "TMAX 560", "year_from": 2020, "engine_code": "562cc Twin"},

        # ==================== BMW (宝马) ====================
        {"key": "BMW|S1000RR|2019|999", "make": "BMW", "model": "S1000RR", "year_from": 2019, "engine_code": "999cc Inline-4"},
        {"key": "BMW|R1250GS|2019|1254", "make": "BMW", "model": "R1250GS", "year_from": 2019, "engine_code": "1254cc Boxer"},
        {"key": "BMW|R1300GS|2024|1300", "make": "BMW", "model": "R1300GS", "year_from": 2024, "engine_code": "1300cc Boxer"},
        {"key": "BMW|F900R|2020|895", "make": "BMW", "model": "F900R", "year_from": 2020, "engine_code": "895cc Twin"},
        {"key": "BMW|G310R|2016|313", "make": "BMW", "model": "G310R", "year_from": 2016, "engine_code": "313cc Single"},
        {"key": "BMW|G310GS|2017|313", "make": "BMW", "model": "G310GS", "year_from": 2017, "engine_code": "313cc Single"},

        # ==================== DUCATI (杜卡迪) ====================
        {"key": "DUCATI|V4S|2020|1103", "make": "Ducati", "model": "Panigale V4 S", "year_from": 2020, "engine_code": "1103cc V4"},
        {"key": "DUCATI|V2|2020|955", "make": "Ducati", "model": "Panigale V2", "year_from": 2020, "engine_code": "955cc V2"},
        {"key": "DUCATI|SFV4|2020|1103", "make": "Ducati", "model": "Streetfighter V4", "year_from": 2020, "engine_code": "1103cc V4"},
        {"key": "DUCATI|MONSTER937|2021|937", "make": "Ducati", "model": "Monster 937", "year_from": 2021, "engine_code": "937cc V2"},
        {"key": "DUCATI|SCRAMBLER800|2015|803", "make": "Ducati", "model": "Scrambler 800", "year_from": 2015, "engine_code": "803cc V2"},

        # ==================== CFMOTO (春风) ====================
        {"key": "CFMOTO|250SR|2019|249", "make": "CFMOTO", "model": "250SR", "year_from": 2019, "engine_code": "249cc Single"},
        {"key": "CFMOTO|450SR|2022|450", "make": "CFMOTO", "model": "450SR", "year_from": 2022, "engine_code": "450cc 270°-Crank"},
        {"key": "CFMOTO|675SR|2024|675", "make": "CFMOTO", "model": "675SR-R", "year_from": 2024, "engine_code": "675cc Triple"},
        {"key": "CFMOTO|450NK|2023|450", "make": "CFMOTO", "model": "450NK", "year_from": 2023, "engine_code": "450cc Twin"},
        {"key": "CFMOTO|800NK|2023|799", "make": "CFMOTO", "model": "800NK", "year_from": 2023, "engine_code": "799cc Twin"},
        {"key": "CFMOTO|800MT|2021|799", "make": "CFMOTO", "model": "800MT", "year_from": 2021, "engine_code": "799cc Twin"},
        {"key": "CFMOTO|700CLX|2020|693", "make": "CFMOTO", "model": "700CL-X", "year_from": 2020, "engine_code": "693cc Twin"},

        # ==================== QJMOTOR (钱江) ====================
        {"key": "QJMOTOR|SRK600|2020|600", "make": "QJMOTOR", "model": "SRK 600 (赛600)", "year_from": 2020, "engine_code": "600cc Inline-4"},
        {"key": "QJMOTOR|SRK400|2022|400", "make": "QJMOTOR", "model": "SRK 400 (赛400)", "year_from": 2022, "engine_code": "400cc Twin"},
        {"key": "QJMOTOR|SRK800|2024|778", "make": "QJMOTOR", "model": "SRK 800RR (赛800)", "year_from": 2024, "engine_code": "778cc Inline-4"},
        {"key": "QJMOTOR|FLASH300|2021|300", "make": "QJMOTOR", "model": "Flash 300S (闪300)", "year_from": 2021, "engine_code": "300cc V2"},
        {"key": "QJMOTOR|SRT800|2021|754", "make": "QJMOTOR", "model": "SRT 800 (骁800)", "year_from": 2021, "engine_code": "754cc Twin"},

        # ==================== KOVE (凯越) ====================
        {"key": "KOVE|321RR|2021|321", "make": "KOVE", "model": "321RR", "year_from": 2021, "engine_code": "321cc Twin"},
        {"key": "KOVE|450RR|2023|443", "make": "KOVE", "model": "450RR", "year_from": 2023, "engine_code": "443cc Inline-4"},
        {"key": "KOVE|800X|2023|799", "make": "KOVE", "model": "800X Super Adventure", "year_from": 2023, "engine_code": "799cc Twin"},

        # ==================== VOGE (无极) ====================
        {"key": "VOGE|525RR|2023|494", "make": "VOGE", "model": "525RR", "year_from": 2023, "engine_code": "494cc Twin"},
        {"key": "VOGE|300RR|2019|292", "make": "VOGE", "model": "300RR", "year_from": 2019, "engine_code": "292cc Single"},
        {"key": "VOGE|525DSX|2023|494", "make": "VOGE", "model": "525DSX", "year_from": 2023, "engine_code": "494cc Twin"},
        {"key": "VOGE|CU525|2023|494", "make": "VOGE", "model": "CU525", "year_from": 2023, "engine_code": "494cc Twin"},
    ]

    for m in motorcycles:
        if not db.query(Vehicle).filter_by(key=m["key"]).first():
            db.add(Vehicle(**m))
    
    db.commit()
    
    # 2. Add a Sample Procedure for Ninja 400 (Most popular)
    v_key = "KAWASAKI|NINJA400|2018|399"
    p_name = "Oil Change (Ninja 400)"
    
    # Check if exists
    if not db.query(Procedure).filter_by(vehicle_key=v_key, name=p_name).first():
        proc = Procedure(vehicle_key=v_key, name=p_name, description="Standard oil and filter change for Ninja 400.")
        db.add(proc)
        db.commit()
        
        steps = [
            {"order": 1, "text": "Place bike on rear stand. Warm up engine for 2 mins.", "tools": "['rear_stand']", "torque": None},
            {"order": 2, "text": "Remove lower fairing (4mm hex).", "tools": "['hex_4mm']", "torque": None},
            {"order": 3, "text": "Remove drain bolt (17mm). Drain oil.", "tools": "['wrench_17mm', 'oil_pan']", "torque": None},
            {"order": 4, "text": "Remove oil filter.", "tools": "['filter_wrench']", "torque": None},
            {"order": 5, "text": "Install new filter. Hand tighten.", "tools": "['hand']", "torque": "{'val': 17, 'unit': 'Nm'}"},
            {"order": 6, "text": "Install drain bolt with new crush washer.", "tools": "['torque_wrench']", "torque": "{'val': 30, 'unit': 'Nm'}"},
            {"order": 7, "text": "Fill 2.0L of 10W-40 Synthetic Oil.", "tools": "['funnel']", "torque": None},
        ]
        
        for s in steps:
            db.add(ProcedureStep(
                procedure_id=proc.id,
                step_order=s['order'],
                instruction=s['text'],
                required_tools=s['tools'],
                torque_spec=s['torque']
            ))
        db.commit()
        
    return {"status": "seeded", "count": len(motorcycles)}
