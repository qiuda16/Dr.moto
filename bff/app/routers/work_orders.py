from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from difflib import SequenceMatcher
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
import html
import uuid
import json
import logging
from datetime import datetime, timezone
from collections import defaultdict
from io import BytesIO
from urllib.parse import quote
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from ..core.config import settings
from ..core.db import get_db
from ..models import (
    WorkOrder,
    WorkOrderAttachment,
    AuditLog,
    VehicleHealthRecord,
    Quote,
    PartCatalogItem,
    PartCatalogProfile,
    AppSetting,
    VehicleCatalogModel,
    VehicleServiceTemplateItem,
    VehicleServiceTemplatePart,
    VehicleServiceTemplateProfile,
    WorkOrderProcessRecord,
    WorkOrderDeliveryChecklist,
    WorkOrderAdvancedProfile,
    WorkOrderServiceSelection,
    VehicleServicePackage,
    VehicleServicePackageItem,
)
from ..integrations.odoo import odoo_client
from ..integrations.mq import event_bus
from ..integrations.obj_storage import obj_storage
from ..schemas.work_order import (
    WorkOrderCreate,
    WorkOrderResponse,
    WorkOrderProcessRecordResponse,
    WorkOrderProcessRecordUpdate,
)
from ..schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerVehicleCreate,
    CustomerVehicleUpdate,
    CustomerVehicleResponse,
    CustomerWithVehiclesResponse,
)
from ..schemas.auth import User
from ..schemas.webhook import StatusUpdateWebhook
from ..schemas.work_order_ops import (
    WorkOrderBulkStatusUpdate,
    WorkOrderBulkStatusResult,
    WorkOrderBulkDeleteRequest,
    WorkOrderServiceSelectionUpdate,
    WorkOrderServiceSelectionReorderRequest,
)
from ..schemas.vehicle_health import VehicleHealthRecordCreate, VehicleHealthRecordResponse
from ..core.security import get_current_user, require_roles
from ..core.text import build_storage_object_name, compact_whitespace, normalize_text
from ..core.store import resolve_store_id
import redis

router = APIRouter(prefix="/mp/workorders", tags=["Work Orders"])
logger = logging.getLogger("bff")
redis_client = redis.Redis.from_url(settings.REDIS_URL)

WORK_ORDER_TRANSITIONS = {
    "draft": {"confirmed", "cancel"},
    "confirmed": {"diagnosing", "quoted", "cancel"},
    "diagnosing": {"quoted", "cancel"},
    "quoted": {"in_progress", "cancel"},
    "in_progress": {"ready", "cancel"},
    "ready": {"done", "cancel"},
    "done": set(),
    "cancel": set(),
}

STATUS_ACTION_LABELS = {
    "confirmed": "confirm",
    "diagnosing": "start_diagnosis",
    "quoted": "create_quote",
    "in_progress": "start_work",
    "ready": "mark_ready",
    "done": "finish",
    "cancel": "cancel",
}


def _is_odoo_record_missing_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return "record does not exist or has been deleted" in message


def _is_odoo_model_missing_error(exc: Exception, model_name: str | None = None) -> bool:
    message = str(exc or "").lower()
    if "object" not in message or "doesn't exist" not in message:
        return False
    return not model_name or model_name.lower() in message


def _default_quick_check() -> dict:
    return {
        "odometer_km": None,
        "battery_voltage": None,
        "tire_front_psi": None,
        "tire_rear_psi": None,
        "engine_noise_note": "",
    }


def _resolve_delivery_default_note(db: Session | None, store_id: str | None) -> str:
    normalized_store_id = compact_whitespace(store_id or "").lower() or settings.DEFAULT_STORE_ID
    if db is None:
        return ""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.store_id == normalized_store_id)
        .order_by(AppSetting.id.desc())
        .first()
    )
    return compact_whitespace(row.default_delivery_note) if row and row.default_delivery_note else ""


def _resolve_store_settings_row(db: Session | None, store_id: str | None) -> AppSetting | None:
    normalized_store_id = compact_whitespace(store_id or "").lower() or settings.DEFAULT_STORE_ID
    if db is None:
        return None
    return (
        db.query(AppSetting)
        .filter(AppSetting.store_id == normalized_store_id)
        .order_by(AppSetting.id.desc())
        .first()
    )


def _resolve_document_branding(db: Session | None, store_id: str | None) -> dict:
    row = _resolve_store_settings_row(db, store_id)
    store_name = compact_whitespace(row.store_name) if row and row.store_name else "机车博士"
    header_note = compact_whitespace(row.document_header_note) if row and row.document_header_note else "摩托车售后服务专业单据"
    customer_footer = (
        compact_whitespace(row.customer_document_footer_note)
        if row and row.customer_document_footer_note
        else "请客户核对维修项目、金额与交车说明后签字确认。"
    )
    internal_footer = (
        compact_whitespace(row.internal_document_footer_note)
        if row and row.internal_document_footer_note
        else "用于门店内部留档、责任追溯与施工复核。"
    )
    service_advice = (
        compact_whitespace(row.default_service_advice)
        if row and row.default_service_advice
        else "建议客户按保养周期复检，并关注油液、制动与轮胎状态。"
    )
    return {
        "store_name": store_name,
        "header_note": header_note,
        "customer_footer_note": customer_footer,
        "internal_footer_note": internal_footer,
        "service_advice": service_advice,
    }


def _default_delivery_checklist(db: Session | None = None, store_id: str | None = None) -> dict:
    return {
        "explained_to_customer": False,
        "returned_old_parts": False,
        "next_service_notified": False,
        "payment_confirmed": False,
        "payment_method": "",
        "payment_amount": None,
        "notes": _resolve_delivery_default_note(db, store_id),
    }


def _default_advanced_profile() -> dict:
    return {
        "assigned_technician": "",
        "service_bay": "",
        "priority": "normal",
        "promised_at": None,
        "estimated_finish_at": None,
        "is_rework": False,
        "is_urgent": False,
        "qc_owner": "",
        "internal_notes": "",
    }


def _ensure_delivery_checklist(db: Session, store_id: str, work_order_uuid: str) -> WorkOrderDeliveryChecklist:
    row = (
        db.query(WorkOrderDeliveryChecklist)
        .filter(
            WorkOrderDeliveryChecklist.store_id == store_id,
            WorkOrderDeliveryChecklist.work_order_uuid == work_order_uuid,
        )
        .first()
    )
    if row:
        if not compact_whitespace(row.notes):
            default_note = _resolve_delivery_default_note(db, store_id)
            if default_note:
                row.notes = default_note
                db.commit()
                db.refresh(row)
        return row
    row = WorkOrderDeliveryChecklist(
        store_id=store_id,
        work_order_uuid=work_order_uuid,
        notes=_resolve_delivery_default_note(db, store_id) or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _ensure_advanced_profile(db: Session, store_id: str, work_order_uuid: str) -> WorkOrderAdvancedProfile:
    row = (
        db.query(WorkOrderAdvancedProfile)
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrderAdvancedProfile.work_order_uuid == work_order_uuid,
        )
        .first()
    )
    if row:
        return row
    row = WorkOrderAdvancedProfile(store_id=store_id, work_order_uuid=work_order_uuid, priority="normal")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _delivery_checklist_to_response(row: WorkOrderDeliveryChecklist | None, db: Session | None = None, store_id: str | None = None) -> dict:
    if not row:
        return _default_delivery_checklist(db, store_id)
    return {
        "explained_to_customer": bool(row.explained_to_customer),
        "returned_old_parts": bool(row.returned_old_parts),
        "next_service_notified": bool(row.next_service_notified),
        "payment_confirmed": bool(row.payment_confirmed),
        "payment_method": row.payment_method or "",
        "payment_amount": row.payment_amount,
        "notes": row.notes or "",
    }


def _advanced_profile_to_response(row: WorkOrderAdvancedProfile | None) -> dict:
    if not row:
        return _default_advanced_profile()
    return {
        "assigned_technician": row.assigned_technician or "",
        "service_bay": row.service_bay or "",
        "priority": row.priority or "normal",
        "promised_at": row.promised_at.isoformat() if row.promised_at else None,
        "estimated_finish_at": row.estimated_finish_at.isoformat() if row.estimated_finish_at else None,
        "is_rework": bool(row.is_rework),
        "is_urgent": bool(row.is_urgent),
        "qc_owner": row.qc_owner or "",
        "internal_notes": row.internal_notes or "",
    }


def _ensure_process_record(db: Session, store_id: str, work_order_uuid: str, draft_symptom: str | None = None) -> WorkOrderProcessRecord:
    row = (
        db.query(WorkOrderProcessRecord)
        .filter(
            WorkOrderProcessRecord.store_id == store_id,
            WorkOrderProcessRecord.work_order_uuid == work_order_uuid,
        )
        .first()
    )
    if row:
        if row.quick_check_json is None:
            row.quick_check_json = _default_quick_check()
            db.commit()
            db.refresh(row)
        return row

    row = WorkOrderProcessRecord(
        store_id=store_id,
        work_order_uuid=work_order_uuid,
        symptom_draft=draft_symptom,
        symptom_confirmed=None,
        quick_check_json=_default_quick_check(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _process_record_to_response(work_order_uuid: str, row: WorkOrderProcessRecord | None) -> dict:
    if not row:
        return {
            "work_order_id": work_order_uuid,
            "symptom_draft": None,
            "symptom_confirmed": None,
            "quick_check": _default_quick_check(),
        }
    quick_check = row.quick_check_json if isinstance(row.quick_check_json, dict) else _default_quick_check()
    return {
        "work_order_id": work_order_uuid,
        "symptom_draft": row.symptom_draft,
        "symptom_confirmed": row.symptom_confirmed,
        "quick_check": quick_check,
    }


def _parse_iso_datetime(value: str | None):
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {value}") from exc

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _load_store_work_order(db: Session, order_id: str, store_id: str) -> WorkOrder | None:
    return (
        db.query(WorkOrder)
        .filter(WorkOrder.uuid == order_id, WorkOrder.store_id == store_id)
        .first()
    )


def _delete_work_order(db: Session, work_order: WorkOrder):
    if work_order.odoo_id:
        try:
            odoo_client.execute_kw("drmoto.work.order", "unlink", [[work_order.odoo_id]])
        except Exception as e:
            logger.warning(f"Odoo unlink failed for work order {work_order.uuid}: {e}")
    db.query(WorkOrderAttachment).filter(
        WorkOrderAttachment.store_id == work_order.store_id,
        WorkOrderAttachment.work_order_uuid == work_order.uuid,
    ).delete(synchronize_session=False)
    db.query(Quote).filter(
        Quote.store_id == work_order.store_id,
        Quote.work_order_uuid == work_order.uuid,
    ).delete(synchronize_session=False)
    db.delete(work_order)


def _find_catalog_model_id(
    db: Session,
    make: str | None,
    model: str | None,
    year: int | None,
    engine_code: str | None = None,
) -> int | None:
    if not make or not model or not isinstance(year, int):
        return None
    normalized_engine = normalize_text(engine_code)
    if normalized_engine:
        row = (
            db.query(VehicleCatalogModel.id)
            .filter(
                VehicleCatalogModel.is_active.is_(True),
                VehicleCatalogModel.brand == make,
                VehicleCatalogModel.model_name == model,
                VehicleCatalogModel.year_from <= year,
                VehicleCatalogModel.year_to >= year,
                VehicleCatalogModel.default_engine_code == normalized_engine,
            )
            .order_by(VehicleCatalogModel.id.asc())
            .first()
        )
        if row:
            return int(row[0])
    row = (
        db.query(VehicleCatalogModel.id)
        .filter(
            VehicleCatalogModel.is_active.is_(True),
            VehicleCatalogModel.brand == make,
            VehicleCatalogModel.model_name == model,
            VehicleCatalogModel.year_from <= year,
            VehicleCatalogModel.year_to >= year,
        )
        .order_by(VehicleCatalogModel.id.asc())
        .first()
    )
    return int(row[0]) if row else None


def _extract_odoo_many2one_id(value) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, (list, tuple)) and value:
        raw_id = value[0]
        if isinstance(raw_id, int):
            return raw_id if raw_id > 0 else None
        if isinstance(raw_id, str) and raw_id.strip().isdigit():
            parsed = int(raw_id.strip())
            return parsed if parsed > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _normalize_plate_search(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _plate_match_score(query: str, plate: str | None) -> float:
    query_norm = _normalize_plate_search(query)
    plate_norm = _normalize_plate_search(plate)
    if not query_norm or not plate_norm:
        return 0.0
    if query_norm == plate_norm:
        return 120.0
    score = 0.0
    if plate_norm.startswith(query_norm):
        score += 80.0
    elif query_norm in plate_norm:
        score += 55.0
    score += SequenceMatcher(None, query_norm, plate_norm).ratio() * 20.0
    return score


def _normalize_generic_search(value: str | None) -> str:
    return compact_whitespace(str(value or "")).lower()


def _generic_match_score(query: str, target: str | None) -> float:
    query_norm = _normalize_generic_search(query)
    target_norm = _normalize_generic_search(target)
    if not query_norm or not target_norm:
        return 0.0
    if query_norm == target_norm:
        return 120.0
    score = 0.0
    if target_norm.startswith(query_norm):
        score += 80.0
    elif query_norm in target_norm:
        score += 55.0
    score += SequenceMatcher(None, query_norm, target_norm).ratio() * 20.0
    return score


def _customer_match_score(query: str, partner: dict, vehicles: list[dict] | None = None) -> float:
    score = 0.0
    score += _generic_match_score(query, partner.get("name")) * 1.5
    score += _generic_match_score(query, partner.get("phone")) * 1.35
    score += _generic_match_score(query, partner.get("email")) * 0.6
    for vehicle in vehicles or []:
        score += _plate_match_score(query, vehicle.get("license_plate")) * 0.8
        score += _generic_match_score(query, vehicle.get("vin")) * 0.35
        score += _generic_match_score(query, f"{vehicle.get('make') or ''} {vehicle.get('model') or ''}") * 0.7
    return score


def _parse_positive_int(value) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.isdigit():
            parsed = int(normalized)
            return parsed if parsed > 0 else None
    return None


def _require_positive_int(value, field_name: str) -> int:
    parsed = _parse_positive_int(value)
    if parsed is None:
        raise HTTPException(status_code=400, detail=f"{field_name} must be a positive integer")
    return parsed


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _serialize_template_required_parts(db: Session, template_item_ids: list[int]) -> dict[int, list[dict]]:
    if not template_item_ids:
        return {}

    rows = (
        db.query(VehicleServiceTemplatePart)
        .filter(VehicleServiceTemplatePart.template_item_id.in_(template_item_ids))
        .order_by(VehicleServiceTemplatePart.sort_order.asc(), VehicleServiceTemplatePart.id.asc())
        .all()
    )
    part_ids = [row.part_id for row in rows if row.part_id]
    part_map = {row.id: row for row in db.query(PartCatalogItem).filter(PartCatalogItem.id.in_(part_ids)).all()} if part_ids else {}
    profile_map = {
        row.part_id: row for row in db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id.in_(part_ids)).all()
    } if part_ids else {}

    grouped: dict[int, list[dict]] = {}
    for row in rows:
        part = part_map.get(row.part_id) if row.part_id else None
        profile = profile_map.get(row.part_id) if row.part_id else None
        grouped.setdefault(row.template_item_id, []).append(
            {
                "id": row.id,
                "part_id": row.part_id,
                "part_no": row.part_no or (part.part_no if part else None),
                "part_name": row.part_name or (part.name if part else ""),
                "qty": row.qty,
                "unit_price": row.unit_price if row.unit_price is not None else (profile.sale_price if profile else None),
                "notes": row.notes,
                "sort_order": row.sort_order,
                "is_optional": row.is_optional,
            }
        )
    return grouped


def _service_template_to_dict(
    row: VehicleServiceTemplateItem,
    profile: VehicleServiceTemplateProfile | None,
    required_parts: list[dict] | None = None,
) -> dict:
    required_parts = required_parts or []
    parts_total = round(
        sum(float(item.get("qty") or 0) * float(item.get("unit_price") or 0) for item in required_parts),
        2,
    )
    labor_price = float(profile.labor_price) if profile and profile.labor_price is not None else 0.0
    suggested_price = (
        float(profile.suggested_price)
        if profile and profile.suggested_price is not None
        else round(parts_total + labor_price, 2)
    )
    return {
        "template_item_id": row.id,
        "service_name": row.part_name,
        "service_code": row.part_code,
        "repair_method": row.repair_method,
        "labor_hours": row.labor_hours,
        "labor_price": labor_price,
        "suggested_price": suggested_price,
        "notes": row.notes,
        "sort_order": row.sort_order,
        "required_parts": required_parts,
        "parts_total": parts_total,
    }


def _service_selection_to_dict(row: WorkOrderServiceSelection) -> dict:
    required_parts = row.required_parts_json if isinstance(row.required_parts_json, list) else []
    parts_total = round(
        sum(float(item.get("qty") or 0) * float(item.get("unit_price") or 0) for item in required_parts),
        2,
    )
    labor_total = round(float(row.labor_price or 0), 2)
    line_total = round(float(row.suggested_price or (parts_total + labor_total)), 2)
    return {
        "id": row.id,
        "template_item_id": row.template_item_id,
        "service_name": row.service_name,
        "service_code": row.service_code,
        "repair_method": row.repair_method,
        "labor_hours": row.labor_hours,
        "labor_price": labor_total,
        "suggested_price": line_total,
        "notes": row.notes,
        "sort_order": row.sort_order,
        "required_parts": required_parts,
        "parts_total": parts_total,
        "line_total": line_total,
    }


def _service_package_interval_label(row: VehicleServicePackage) -> str:
    parts: list[str] = []
    if row.recommended_interval_km:
        parts.append(f"{int(row.recommended_interval_km)} km")
    if row.recommended_interval_months:
        parts.append(f"{int(row.recommended_interval_months)} 个月")
    return " / ".join(parts) if parts else "按需推荐"


def _serialize_service_packages_for_work_order(
    db: Session,
    model_id: int,
    selected_template_item_ids: set[int] | None = None,
) -> list[dict]:
    selected_template_item_ids = selected_template_item_ids or set()
    try:
        from .catalog import _ensure_baseline_service_packages_for_model

        created = _ensure_baseline_service_packages_for_model(db, model_id)
        if created:
            db.commit()
        else:
            db.flush()
    except Exception as exc:
        logger.warning("Service package baseline ensure failed for model %s: %s", model_id, exc)
    package_rows = (
        db.query(VehicleServicePackage)
        .filter(
            VehicleServicePackage.model_id == model_id,
            VehicleServicePackage.is_active.is_(True),
        )
        .order_by(VehicleServicePackage.sort_order.asc(), VehicleServicePackage.id.asc())
        .all()
    )
    if not package_rows:
        return []

    package_ids = [row.id for row in package_rows]
    item_rows = (
        db.query(VehicleServicePackageItem, VehicleServiceTemplateItem, VehicleServiceTemplateProfile)
        .join(VehicleServiceTemplateItem, VehicleServiceTemplateItem.id == VehicleServicePackageItem.template_item_id)
        .outerjoin(
            VehicleServiceTemplateProfile,
            VehicleServiceTemplateProfile.template_item_id == VehicleServiceTemplateItem.id,
        )
        .filter(VehicleServicePackageItem.package_id.in_(package_ids))
        .order_by(
            VehicleServicePackageItem.package_id.asc(),
            VehicleServicePackageItem.sort_order.asc(),
            VehicleServicePackageItem.id.asc(),
        )
        .all()
    )
    parts_map = _serialize_template_required_parts(
        db,
        [template_row.id for _, template_row, _ in item_rows],
    )
    grouped_items: dict[int, list[dict]] = defaultdict(list)
    for package_item, template_row, profile_row in item_rows:
        template_payload = _service_template_to_dict(
            template_row,
            profile_row,
            parts_map.get(template_row.id, []),
        )
        template_payload["is_optional"] = bool(package_item.is_optional)
        template_payload["package_item_notes"] = package_item.notes
        grouped_items[package_item.package_id].append(template_payload)

    serialized: list[dict] = []
    for row in package_rows:
        items = grouped_items.get(row.id, [])
        template_ids = [int(item["template_item_id"]) for item in items]
        already_selected = [item_id for item_id in template_ids if item_id in selected_template_item_ids]
        available_ids = [item_id for item_id in template_ids if item_id not in selected_template_item_ids]
        serialized.append(
            {
                "id": row.id,
                "package_name": row.package_name,
                "package_code": row.package_code,
                "description": row.description,
                "recommended_interval_km": row.recommended_interval_km,
                "recommended_interval_months": row.recommended_interval_months,
                "interval_label": _service_package_interval_label(row),
                "labor_hours_total": float(row.labor_hours_total or 0),
                "labor_price_total": float(row.labor_price_total or 0),
                "parts_price_total": float(row.parts_price_total or 0),
                "suggested_price_total": float(row.suggested_price_total or 0),
                "items": items,
                "item_count": len(items),
                "already_selected_count": len(already_selected),
                "available_count": len(available_ids),
                "is_fully_selected": len(available_ids) == 0 and len(items) > 0,
            }
        )
    return serialized


def _load_work_order_service_selections(db: Session, store_id: str, order_id: str) -> list[WorkOrderServiceSelection]:
    return (
        db.query(WorkOrderServiceSelection)
        .filter(
            WorkOrderServiceSelection.store_id == store_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
        )
        .order_by(WorkOrderServiceSelection.sort_order.asc(), WorkOrderServiceSelection.id.asc())
        .all()
    )


def _load_work_order_selected_items(db: Session, store_id: str, order_id: str) -> list[dict]:
    return [_service_selection_to_dict(row) for row in _load_work_order_service_selections(db, store_id, order_id)]


def _get_latest_vehicle_health_record(
    db: Session,
    store_id: str,
    customer_id: str | None,
    vehicle_plate: str | None,
) -> VehicleHealthRecord | None:
    customer_text = compact_whitespace(customer_id)
    plate_text = compact_whitespace(vehicle_plate)
    if not customer_text or not plate_text:
        return None
    return (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == customer_text,
            VehicleHealthRecord.vehicle_plate == plate_text,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )


def _get_work_order_delivery_checklist(
    db: Session,
    store_id: str,
    work_order_uuid: str,
) -> WorkOrderDeliveryChecklist | None:
    return (
        db.query(WorkOrderDeliveryChecklist)
        .filter(
            WorkOrderDeliveryChecklist.store_id == store_id,
            WorkOrderDeliveryChecklist.work_order_uuid == work_order_uuid,
        )
        .first()
    )


def _get_work_order_quote_summary(
    db: Session,
    store_id: str,
    work_order_uuid: str,
    active_quote_version: int | None = None,
) -> dict:
    quote_rows = (
        db.query(Quote)
        .filter(
            Quote.work_order_uuid == work_order_uuid,
            Quote.store_id == store_id,
        )
        .order_by(Quote.version.desc())
        .all()
    )
    latest_quote = quote_rows[0] if quote_rows else None
    active_quote = next((row for row in quote_rows if row.is_active), None)
    if not active_quote and active_quote_version is not None:
        active_quote = next((row for row in quote_rows if row.version == active_quote_version), None)
    return {
        "rows": quote_rows,
        "latest": latest_quote,
        "active": active_quote,
        "has_effective_quote": bool(active_quote and active_quote.status in {"published", "confirmed"}),
        "active_version": active_quote_version,
    }


def _build_work_order_workflow_checks(
    db: Session,
    store_id: str,
    db_wo: WorkOrder,
    selected_items: list[dict] | None = None,
) -> dict:
    selected_items = selected_items if selected_items is not None else _load_work_order_selected_items(db, store_id, db_wo.uuid)
    has_selected_items = bool(selected_items)
    quote_summary = _get_work_order_quote_summary(db, store_id, db_wo.uuid, db_wo.active_quote_version)
    has_effective_quote = quote_summary["has_effective_quote"]
    latest_health = _get_latest_vehicle_health_record(db, store_id, db_wo.customer_id, db_wo.vehicle_plate)
    has_health_record = latest_health is not None
    delivery_row = _get_work_order_delivery_checklist(db, store_id, db_wo.uuid)
    delivery_saved = delivery_row is not None
    delivery_complete = bool(
        delivery_row
        and delivery_row.explained_to_customer
        and delivery_row.payment_confirmed
        and compact_whitespace(delivery_row.payment_method)
        and delivery_row.payment_amount is not None
    )

    checkpoints = [
        {
            "key": "selected_services",
            "label": "已选择维修项目",
            "done": has_selected_items,
            "hint": "至少选择一个维修/保养项目，报价和施工才有依据。",
        },
        {
            "key": "effective_quote",
            "label": "已形成有效报价",
            "done": has_effective_quote,
            "hint": "进入施工前，建议至少有一版已发布或已确认的报价，方便对客和留档一致。",
        },
        {
            "key": "health_record",
            "label": "已完成完工体检",
            "done": has_health_record,
            "hint": "施工完成后应补一次整车体检，交付单会带出最近记录。",
        },
        {
            "key": "delivery_checklist",
            "label": "已完成交车确认",
            "done": delivery_complete,
            "hint": "需要说明维修内容、确认收款方式和金额后，再完成交车。",
        },
    ]

    gates = {
        "quoted": [],
        "in_progress": [],
        "ready": [],
        "done": [],
    }
    if not has_selected_items:
        gates["quoted"].append("请先选择至少一个维修项目")
        gates["in_progress"].append("请先选择至少一个维修项目")
        gates["ready"].append("请先选择至少一个维修项目")
        gates["done"].append("请先选择至少一个维修项目")
    if not has_effective_quote:
        gates["in_progress"].append("请先生成并发布一版有效报价")
        gates["ready"].append("请先生成并发布一版有效报价")
        gates["done"].append("请先生成并发布一版有效报价")
    if not has_health_record:
        gates["ready"].append("请先完成整车体检并保存记录")
        gates["done"].append("请先完成整车体检并保存记录")
    if not delivery_saved:
        gates["done"].append("请先填写交车确认清单")
    elif not delivery_complete:
        gates["done"].append("请补全交车说明、收款方式和收款金额")

    return {
        "checkpoints": checkpoints,
        "quote_ready": has_effective_quote,
        "latest_health_record_at": latest_health.measured_at.isoformat() if latest_health and latest_health.measured_at else None,
        "delivery_checklist_saved": delivery_saved,
        "delivery_checklist_complete": delivery_complete,
        "gates": {
            target_status: {
                "ready": len(messages) == 0,
                "missing": messages,
            }
            for target_status, messages in gates.items()
        },
    }


def _validate_transition_prerequisites(
    db: Session,
    store_id: str,
    db_wo: WorkOrder,
    target_status: str,
) -> None:
    workflow_checks = _build_work_order_workflow_checks(db, store_id, db_wo)
    gate = workflow_checks["gates"].get(target_status)
    if gate and not gate["ready"]:
        raise HTTPException(
            status_code=409,
            detail="；".join(gate["missing"]),
        )


def _inject_document_sections(html_text: str, sections: list[str]) -> str:
    if not html_text or not sections:
        return html_text
    extra = "".join(section for section in sections if section)
    if not extra:
        return html_text
    return html_text.replace("</body>", f"{extra}</body>") if "</body>" in html_text else f"{html_text}{extra}"


def _render_selected_services_section(doc_type: str, selected_items: list[dict]) -> str:
    if doc_type not in {"work-order", "quote", "delivery-note"} or not selected_items:
        return ""

    rows = []
    for item in selected_items:
        parts = item.get("required_parts") or []
        parts_text = "、".join(
            f"{part.get('part_name') or '-'} x{part.get('qty') or 0}"
            for part in parts
            if part.get("part_name")
        ) or "无"
        method = compact_whitespace(item.get("repair_method") or "") or "按门店标准作业执行"
        notes = compact_whitespace(item.get("notes") or "") or "-"
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(item.get("service_name") or '-'))}</td>
              <td>{html.escape(method)}</td>
              <td>{html.escape(parts_text)}</td>
              <td>{html.escape(str(item.get("parts_total") or 0))}</td>
              <td>{html.escape(str(item.get("labor_price") or 0))}</td>
              <td>{html.escape(str(item.get("line_total") or 0))}</td>
              <td>{html.escape(notes)}</td>
            </tr>
            """
        )

    title = {
        "work-order": "标准维修项目留档",
        "quote": "标准维修项目报价依据",
        "delivery-note": "已执行维修项目复核",
    }.get(doc_type, "维修项目")
    hint = {
        "work-order": "以下项目来自车型标准维修库并已加入当前工单，便于留档与复盘。",
        "quote": "以下项目作为本次报价的标准项目依据，客户确认后应与正式施工项目保持一致。",
        "delivery-note": "以下项目为本次交付前复核的施工内容，可作为客户沟通和交付说明依据。",
    }.get(doc_type, "")
    return f"""
<section class="doc-addon">
  <style>
    .doc-addon {{ max-width: 980px; margin: 16px auto 0; font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; color: #1f2937; }}
    .doc-addon .box {{ border: 1px solid #d7dfeb; padding: 14px; border-radius: 12px; margin-top: 14px; background: #fff; }}
    .doc-addon h2 {{ margin: 0 0 10px; font-size: 16px; color: #172554; }}
    .doc-addon .note {{ margin: 0 0 10px; color: #475569; font-size: 13px; line-height: 1.7; }}
    .doc-addon table {{ width: 100%; border-collapse: collapse; }}
    .doc-addon th, .doc-addon td {{ border: 1px solid #dbe2ec; padding: 9px 10px; font-size: 13px; vertical-align: top; text-align: left; }}
    .doc-addon th {{ background: #f5f7fb; color: #334155; }}
  </style>
  <div class="box">
    <h2>{html.escape(title)}</h2>
    <p class="note">{html.escape(hint)}</p>
    <table>
      <thead>
        <tr>
          <th>维修项目</th>
          <th>标准方法</th>
          <th>所需配件</th>
          <th>配件费</th>
          <th>工时费</th>
          <th>项目合计</th>
          <th>备注</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</section>
"""


def _payment_method_label(value: str | None) -> str:
    return {
        "cash": "现金",
        "wechat": "微信",
        "alipay": "支付宝",
        "bank_card": "银行卡",
        "other": "其他",
    }.get((value or "").strip(), value or "-")


def _render_delivery_checklist_section(doc_type: str, checklist: dict | None) -> str:
    if doc_type not in {"delivery-note", "work-order"} or not checklist:
        return ""

    yes_no = lambda flag: "已确认" if flag else "未确认"
    rows = [
        ("维修/保养内容已向客户说明", yes_no(checklist.get("explained_to_customer"))),
        ("旧件返还或处理方式已确认", yes_no(checklist.get("returned_old_parts"))),
        ("下次保养提醒已告知", yes_no(checklist.get("next_service_notified"))),
        ("线下收款已确认", yes_no(checklist.get("payment_confirmed"))),
        ("收款方式", _payment_method_label(checklist.get("payment_method"))),
        ("收款金额", str(checklist.get("payment_amount") if checklist.get("payment_amount") is not None else "-")),
        ("交车备注", compact_whitespace(checklist.get("notes") or "") or "-"),
    ]
    row_html = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    return f"""
<section class="doc-addon">
  <style>
    .doc-addon {{ max-width: 980px; margin: 16px auto 0; font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; color: #1f2937; }}
    .doc-addon .box {{ border: 1px solid #d7dfeb; padding: 14px; border-radius: 12px; margin-top: 14px; background: #fff; }}
    .doc-addon h2 {{ margin: 0 0 10px; font-size: 16px; color: #172554; }}
    .doc-addon table {{ width: 100%; border-collapse: collapse; }}
    .doc-addon th, .doc-addon td {{ border: 1px solid #dbe2ec; padding: 9px 10px; font-size: 13px; vertical-align: top; text-align: left; }}
    .doc-addon th {{ background: #f5f7fb; color: #334155; }}
  </style>
  <div class="box">
    <h2>交车确认留档</h2>
    <table>
      <thead>
        <tr><th>项目</th><th>结果</th></tr>
      </thead>
      <tbody>{row_html}</tbody>
    </table>
  </div>
</section>
"""


def _render_advanced_profile_section(doc_type: str, advanced_profile: dict | None) -> str:
    if doc_type != "work-order" or not advanced_profile:
        return ""
    if not any(
        [
            advanced_profile.get("assigned_technician"),
            advanced_profile.get("service_bay"),
            advanced_profile.get("qc_owner"),
            advanced_profile.get("internal_notes"),
            advanced_profile.get("promised_at"),
            advanced_profile.get("estimated_finish_at"),
            advanced_profile.get("is_rework"),
            advanced_profile.get("is_urgent"),
            advanced_profile.get("priority") not in (None, "", "normal"),
        ]
    ):
        return ""
    rows = [
        ("指派技师", advanced_profile.get("assigned_technician") or "-"),
        ("施工工位", advanced_profile.get("service_bay") or "-"),
        ("优先级", {"normal": "普通", "high": "优先", "urgent": "加急"}.get(advanced_profile.get("priority"), "普通")),
        ("承诺交车时间", advanced_profile.get("promised_at") or "-"),
        ("预计完工时间", advanced_profile.get("estimated_finish_at") or "-"),
        ("质检责任人", advanced_profile.get("qc_owner") or "-"),
        ("返修工单", "是" if advanced_profile.get("is_rework") else "否"),
        ("加急处理", "是" if advanced_profile.get("is_urgent") else "否"),
        ("内部备注", compact_whitespace(advanced_profile.get("internal_notes") or "") or "-"),
    ]
    row_html = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return f"""
<section class="doc-addon">
  <style>
    .doc-addon {{ max-width: 980px; margin: 16px auto 0; font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; color: #1f2937; }}
    .doc-addon .box {{ border: 1px solid #d7dfeb; padding: 14px; border-radius: 12px; margin-top: 14px; background: #fff; }}
    .doc-addon h2 {{ margin: 0 0 10px; font-size: 16px; color: #172554; }}
    .doc-addon table {{ width: 100%; border-collapse: collapse; }}
    .doc-addon th, .doc-addon td {{ border: 1px solid #dbe2ec; padding: 9px 10px; font-size: 13px; vertical-align: top; text-align: left; }}
    .doc-addon th {{ background: #f5f7fb; color: #334155; }}
  </style>
  <div class="box">
    <h2>调度与质检摘要</h2>
    <table>
      <tbody>{row_html}</tbody>
    </table>
  </div>
</section>
"""


def _resolve_vehicle_input(db: Session, vehicle: CustomerVehicleCreate | CustomerVehicleUpdate) -> dict:
    payload = {
        "catalog_model_id": getattr(vehicle, "catalog_model_id", None),
        "license_plate": normalize_text(getattr(vehicle, "license_plate", None)),
        "make": normalize_text(getattr(vehicle, "make", None)),
        "model": normalize_text(getattr(vehicle, "model", None)),
        "year": getattr(vehicle, "year", None),
        "engine_code": normalize_text(getattr(vehicle, "engine_code", None)),
        "vin": normalize_text(getattr(vehicle, "vin", None)),
        "color": normalize_text(getattr(vehicle, "color", None)),
    }
    catalog_model_id = payload.get("catalog_model_id")
    if isinstance(catalog_model_id, int):
        catalog = (
            db.query(VehicleCatalogModel)
            .filter(
                VehicleCatalogModel.id == catalog_model_id,
                VehicleCatalogModel.is_active.is_(True),
            )
            .first()
        )
        if not catalog:
            raise HTTPException(status_code=400, detail="catalog_model_id is invalid")
        payload["make"] = catalog.brand
        payload["model"] = catalog.model_name
        if not isinstance(payload["year"], int):
            payload["year"] = catalog.year_to or catalog.year_from
        if not payload["engine_code"]:
            payload["engine_code"] = catalog.default_engine_code
        if payload["year"] < catalog.year_from or payload["year"] > catalog.year_to:
            raise HTTPException(
                status_code=400,
                detail=f"year must be in [{catalog.year_from}, {catalog.year_to}] for selected catalog model",
            )
    return payload


def _build_vehicle_key(vehicle: dict) -> str:
    engine = vehicle.get("engine_code") or "-"
    make = vehicle.get("make") or ""
    model = vehicle.get("model") or ""
    year = vehicle.get("year") or ""
    return f"{make}|{model}|{year}|{engine}".upper()


def _catalog_vehicle_key(model_id: int) -> str:
    return f"CATALOG_MODEL:{model_id}"


def _resolve_work_order_vehicle_key(
    db: Session,
    customer_id: int | None,
    vehicle_plate: str | None,
) -> str | None:
    plate = compact_whitespace(vehicle_plate)
    if not plate:
        return None

    domain = [["license_plate", "=", plate]]
    if isinstance(customer_id, int) and customer_id > 0:
        domain.append(["partner_id", "=", customer_id])

    rows = odoo_client.execute_kw(
        "drmoto.partner.vehicle",
        "search_read",
        [domain],
        {"fields": ["id", "partner_id", "license_plate", "vehicle_id"], "limit": 1},
    )
    if not rows and isinstance(customer_id, int) and customer_id > 0:
        rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["partner_id", "=", customer_id], ["license_plate", "ilike", plate]]],
            {"fields": ["id", "partner_id", "license_plate", "vehicle_id"], "limit": 1},
        )

    if not rows:
        return None

    vehicle_ref = rows[0].get("vehicle_id")
    vehicle_model_id = vehicle_ref[0] if isinstance(vehicle_ref, list) and vehicle_ref else None
    if not vehicle_model_id:
        return None

    vehicle_rows = odoo_client.execute_kw(
        "drmoto.vehicle",
        "read",
        [[vehicle_model_id], ["id", "make", "model", "year_from", "engine_code"]],
    )
    if not vehicle_rows:
        return None

    vehicle_row = vehicle_rows[0]
    catalog_model_id = _find_catalog_model_id(
        db,
        normalize_text(vehicle_row.get("make")),
        normalize_text(vehicle_row.get("model")),
        vehicle_row.get("year_from") if isinstance(vehicle_row.get("year_from"), int) else None,
        normalize_text(vehicle_row.get("engine_code")),
    )
    if isinstance(catalog_model_id, int) and catalog_model_id > 0:
        return _catalog_vehicle_key(catalog_model_id)

    return _build_vehicle_key(
        {
            "make": normalize_text(vehicle_row.get("make")),
            "model": normalize_text(vehicle_row.get("model")),
            "year": vehicle_row.get("year_from"),
            "engine_code": normalize_text(vehicle_row.get("engine_code")),
        }
    )


def _ensure_vehicle_model(vehicle: dict) -> int:
    vehicle_key = _build_vehicle_key(vehicle)
    domain = [["key", "=", vehicle_key]]
    rows = odoo_client.execute_kw("drmoto.vehicle", "search_read", [domain], {"fields": ["id"], "limit": 1})
    if rows:
        return rows[0]["id"]
    vals = {
        "key": vehicle_key,
        "make": vehicle.get("make"),
        "model": vehicle.get("model"),
        "year_from": vehicle.get("year"),
        "year_to": vehicle.get("year"),
        "engine_code": vehicle.get("engine_code"),
    }
    return odoo_client.execute_kw("drmoto.vehicle", "create", [vals])


def _create_partner_vehicle(db: Session, partner_id: int, vehicle: CustomerVehicleCreate) -> dict:
    resolved = _resolve_vehicle_input(db, vehicle)
    vehicle_model_id = _ensure_vehicle_model(resolved)
    vals = {
        "partner_id": partner_id,
        "vehicle_id": vehicle_model_id,
        "license_plate": resolved["license_plate"],
        "vin": resolved["vin"],
        "color": resolved["color"],
    }
    partner_vehicle_id = odoo_client.execute_kw("drmoto.partner.vehicle", "create", [vals])
    result = odoo_client.execute_kw(
        "drmoto.partner.vehicle",
        "read",
        [[partner_vehicle_id], ["id", "partner_id", "license_plate", "vin", "color", "vehicle_id"]],
    )[0]
    vehicle_model = odoo_client.execute_kw(
        "drmoto.vehicle",
        "read",
        [[vehicle_model_id], ["id", "make", "model", "year_from", "engine_code"]],
    )[0]
    return {
        "id": result["id"],
        "partner_id": result["partner_id"][0] if isinstance(result.get("partner_id"), list) else partner_id,
        "catalog_model_id": _find_catalog_model_id(
            db,
            vehicle_model.get("make"),
            vehicle_model.get("model"),
            vehicle_model.get("year_from"),
            vehicle_model.get("engine_code"),
        ),
        "license_plate": result.get("license_plate"),
        "vin": result.get("vin"),
        "color": result.get("color"),
        "vehicle_id": vehicle_model_id,
        "make": vehicle_model.get("make"),
        "model": vehicle_model.get("model"),
        "year": vehicle_model.get("year_from"),
        "engine_code": vehicle_model.get("engine_code"),
    }


def _read_partner_vehicle_detail(db: Session, partner_vehicle_id: int, fallback_partner_id: int | None = None) -> dict:
    result = odoo_client.execute_kw(
        "drmoto.partner.vehicle",
        "read",
        [[partner_vehicle_id], ["id", "partner_id", "license_plate", "vin", "color", "vehicle_id"]],
    )[0]
    vehicle_ref = result.get("vehicle_id")
    vehicle_model_id = vehicle_ref[0] if isinstance(vehicle_ref, list) and vehicle_ref else None
    vehicle_model = {}
    if vehicle_model_id:
        rows = odoo_client.execute_kw(
            "drmoto.vehicle",
            "read",
            [[vehicle_model_id], ["id", "make", "model", "year_from", "engine_code"]],
        )
        vehicle_model = rows[0] if rows else {}
    partner_ref = result.get("partner_id")
    partner_id = partner_ref[0] if isinstance(partner_ref, list) and partner_ref else fallback_partner_id
    return {
        "id": result["id"],
        "partner_id": partner_id,
        "catalog_model_id": _find_catalog_model_id(
            db,
            normalize_text(vehicle_model.get("make")),
            normalize_text(vehicle_model.get("model")),
            vehicle_model.get("year_from") if isinstance(vehicle_model.get("year_from"), int) else None,
            normalize_text(vehicle_model.get("engine_code")),
        ),
        "license_plate": normalize_text(result.get("license_plate")) or "",
        "vin": normalize_text(result.get("vin")),
        "color": normalize_text(result.get("color")),
        "vehicle_id": vehicle_model_id,
        "make": normalize_text(vehicle_model.get("make")),
        "model": normalize_text(vehicle_model.get("model")),
        "year": vehicle_model.get("year_from") if isinstance(vehicle_model.get("year_from"), int) else None,
        "engine_code": normalize_text(vehicle_model.get("engine_code")),
    }


def _to_health_response(row: VehicleHealthRecord, prev: VehicleHealthRecord | None = None) -> dict:
    odometer_delta = None
    days_since_prev = None
    if prev:
        odometer_delta = float(row.odometer_km - prev.odometer_km)
        if row.measured_at and prev.measured_at:
            days_since_prev = (row.measured_at - prev.measured_at).total_seconds() / 86400.0
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "vehicle_plate": row.vehicle_plate,
        "measured_at": row.measured_at,
        "odometer_km": float(row.odometer_km),
        "engine_rpm": row.engine_rpm,
        "battery_voltage": row.battery_voltage,
        "tire_front_psi": row.tire_front_psi,
        "tire_rear_psi": row.tire_rear_psi,
        "coolant_temp_c": row.coolant_temp_c,
        "oil_life_percent": row.oil_life_percent,
        "notes": row.notes,
        "extra": row.extra_json,
        "odometer_delta_from_prev": odometer_delta,
        "days_since_prev": days_since_prev,
    }

@router.post("/customers", response_model=dict)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Create a new customer in Odoo."""
    try:
        vals = {
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email,
        }
        new_id = odoo_client.execute_kw('res.partner', 'create', [vals])
        created_vehicles = []
        for vehicle in customer.vehicles:
            created_vehicles.append(_create_partner_vehicle(db, new_id, vehicle))
        return {
            "id": new_id,
            "name": vals["name"],
            "phone": vals["phone"],
            "email": vals["email"],
            "vehicle_count": len(created_vehicles),
            "vehicles": created_vehicles,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer")


@router.put("/customers/{partner_id}", response_model=dict)
async def update_customer(
    partner_id: int,
    payload: CustomerUpdate,
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    try:
        rows = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [[["id", "=", partner_id]]],
            {"fields": ["id", "name", "phone", "email"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Customer not found")

        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(status_code=400, detail="No fields to update")

        vals = {}
        if "name" in patch:
            vals["name"] = payload.name
        if "phone" in patch:
            vals["phone"] = payload.phone
        if "email" in patch:
            vals["email"] = payload.email
        if not vals:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        odoo_client.execute_kw("res.partner", "write", [[partner_id], vals])
        updated = odoo_client.execute_kw(
            "res.partner",
            "read",
            [[partner_id], ["id", "name", "phone", "email"]],
        )[0]
        return {
            "id": updated["id"],
            "name": normalize_text(updated.get("name")) or "",
            "phone": normalize_text(updated.get("phone")),
            "email": normalize_text(updated.get("email")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update customer")


@router.delete("/customers/{partner_id}")
async def delete_customer(
    partner_id: int,
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    try:
        rows = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [[["id", "=", partner_id]]],
            {"fields": ["id"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Customer not found")
        vehicle_rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["partner_id", "=", partner_id]]],
            {"fields": ["id"]},
        )
        vehicle_ids = [row["id"] for row in vehicle_rows]
        if vehicle_ids:
            odoo_client.execute_kw("drmoto.partner.vehicle", "unlink", [vehicle_ids])
        odoo_client.execute_kw("res.partner", "unlink", [[partner_id]])
        return {"deleted": 1, "partner_id": partner_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete customer")


@router.post("/customers/{partner_id}/vehicles", response_model=CustomerVehicleResponse)
async def create_customer_vehicle(
    partner_id: int,
    vehicle: CustomerVehicleCreate,
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    try:
        customers = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [[["id", "=", partner_id]]],
            {"fields": ["id"], "limit": 1},
        )
        if not customers:
            raise HTTPException(status_code=404, detail="Customer not found")
        return _create_partner_vehicle(db, partner_id, vehicle)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer vehicle create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer vehicle")


@router.put("/customers/{partner_id}/vehicles/{partner_vehicle_id}", response_model=CustomerVehicleResponse)
async def update_customer_vehicle(
    partner_id: int,
    partner_vehicle_id: int,
    payload: CustomerVehicleUpdate,
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    try:
        rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["id", "=", partner_vehicle_id], ["partner_id", "=", partner_id]]],
            {"fields": ["id", "partner_id", "license_plate", "vin", "color", "vehicle_id"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Vehicle record not found")

        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(status_code=400, detail="No fields to update")

        current_vehicle_row = rows[0]
        vals = {}
        if "license_plate" in patch:
            vals["license_plate"] = payload.license_plate
        if "vin" in patch:
            vals["vin"] = payload.vin
        if "color" in patch:
            vals["color"] = payload.color

        vehicle_model_fields = {"catalog_model_id", "make", "model", "year", "engine_code"}
        if any(field in patch for field in vehicle_model_fields):
            current_vehicle_ref = current_vehicle_row.get("vehicle_id")
            current_vehicle_id = current_vehicle_ref[0] if isinstance(current_vehicle_ref, list) and current_vehicle_ref else None
            current_model = {}
            if current_vehicle_id:
                model_rows = odoo_client.execute_kw(
                    "drmoto.vehicle",
                    "read",
                    [[current_vehicle_id], ["id", "make", "model", "year_from", "engine_code"]],
                )
                if model_rows:
                    current_model = model_rows[0]

            merged_make = payload.make if "make" in patch else normalize_text(current_model.get("make"))
            merged_model = payload.model if "model" in patch else normalize_text(current_model.get("model"))
            merged_year = payload.year if "year" in patch else current_model.get("year_from")
            merged_engine = payload.engine_code if "engine_code" in patch else normalize_text(current_model.get("engine_code"))

            catalog_model_id = payload.catalog_model_id if "catalog_model_id" in patch else None
            if isinstance(catalog_model_id, int):
                catalog = (
                    db.query(VehicleCatalogModel)
                    .filter(
                        VehicleCatalogModel.id == catalog_model_id,
                        VehicleCatalogModel.is_active.is_(True),
                    )
                    .first()
                )
                if not catalog:
                    raise HTTPException(status_code=400, detail="catalog_model_id is invalid")
                merged_make = catalog.brand
                merged_model = catalog.model_name
                merged_year = merged_year if isinstance(merged_year, int) else (catalog.year_to or catalog.year_from)
                merged_engine = merged_engine or catalog.default_engine_code
                if merged_year < catalog.year_from or merged_year > catalog.year_to:
                    raise HTTPException(
                        status_code=400,
                        detail=f"year must be in [{catalog.year_from}, {catalog.year_to}] for selected catalog model",
                    )

            if not merged_make or not merged_model or not isinstance(merged_year, int):
                raise HTTPException(status_code=400, detail="make/model/year are required to save vehicle model fields")

            model_key = f"{merged_make}|{merged_model}|{merged_year}|{merged_engine or '-'}".upper()
            found = odoo_client.execute_kw(
                "drmoto.vehicle",
                "search_read",
                [[["key", "=", model_key]]],
                {"fields": ["id"], "limit": 1},
            )
            if found:
                merged_vehicle_model_id = found[0]["id"]
            else:
                merged_vehicle_model_id = odoo_client.execute_kw(
                    "drmoto.vehicle",
                    "create",
                    [{
                        "key": model_key,
                        "make": merged_make,
                        "model": merged_model,
                        "year_from": merged_year,
                        "year_to": merged_year,
                        "engine_code": merged_engine,
                    }],
                )
            vals["vehicle_id"] = merged_vehicle_model_id

        if not vals:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        odoo_client.execute_kw("drmoto.partner.vehicle", "write", [[partner_vehicle_id], vals])
        return _read_partner_vehicle_detail(db, partner_vehicle_id, fallback_partner_id=partner_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer vehicle update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update customer vehicle")


@router.delete("/customers/{partner_id}/vehicles/{partner_vehicle_id}")
async def delete_customer_vehicle(
    partner_id: int,
    partner_vehicle_id: int,
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    try:
        rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["id", "=", partner_vehicle_id], ["partner_id", "=", partner_id]]],
            {"fields": ["id"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Vehicle record not found")
        odoo_client.execute_kw("drmoto.partner.vehicle", "unlink", [[partner_vehicle_id]])
        return {"deleted": 1, "partner_vehicle_id": partner_vehicle_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer vehicle delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete customer vehicle")


@router.post("/{order_id}/upload")
async def upload_attachment(
    order_id: str,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    store_id = resolve_store_id(request, current_user)
    # 1. Verify Work Order
    wo = _load_store_work_order(db, order_id, store_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    # 2. Upload to MinIO
    try:
        contents = await file.read()
        object_name = build_storage_object_name(f"work-orders/{order_id}", file.filename)
        file_url = obj_storage.put_bytes(object_name, contents, file.content_type)
        
        # 3. Record in DB
        attachment = WorkOrderAttachment(
            store_id=store_id,
            work_order_uuid=order_id,
            file_name=file.filename,
            file_url=file_url
        )
        db.add(attachment)
        db.commit()
        
        # 4. Notify (Audit/Odoo)
        event_bus.publish("evt:media_uploaded", {"uuid": order_id, "url": file_url})
        
        return {"filename": file.filename, "url": file_url}
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/callback/status", tags=["Webhooks"])
async def update_work_order_status(
    payload: StatusUpdateWebhook,
    request: Request,
    db: Session = Depends(get_db)
):
    """Webhook called by Odoo when status changes."""
    expected_secret = settings.WEBHOOK_SHARED_SECRET
    if expected_secret:
        incoming_secret = request.headers.get("X-Webhook-Secret")
        if incoming_secret != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == payload.bff_uuid).first()
    if not wo:
        logger.warning(f"Webhook: WorkOrder not found for UUID {payload.bff_uuid}")
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    if wo.status != payload.new_status:
        logger.info(f"Syncing status for {wo.uuid}: {wo.status} -> {payload.new_status}")
        wo.status = payload.new_status
        db.commit()
        
        # Publish event
        event_bus.publish("evt:work_order_updated", {"uuid": wo.uuid, "status": wo.status})
        
    return {"status": "updated"}

@router.post("/", response_model=WorkOrderResponse)
async def create_work_order(
    order_in: WorkOrderCreate, 
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    store_id = resolve_store_id(request, current_user)
    idem_key = None
    if request:
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            cached = redis_client.get(f"idempotency:wo:create:{store_id}:{idem_key}")
            if cached:
                return json.loads(cached.decode("utf-8"))

    # 1. Create in Odoo
    try:
        customer_id = _require_positive_int(order_in.customer_id, "customer_id")
        odoo_payload = {
            'name': 'New', # Will be auto-numbered
            'customer_id': customer_id,
            'vehicle_plate': order_in.vehicle_plate,
            'description': order_in.description,
            'bff_uuid': "pending", # We will update this later or generate here
        }
        
        # Add procedure_id if present
        if hasattr(order_in, 'procedure_id') and order_in.procedure_id:
             odoo_payload['procedure_id'] = order_in.procedure_id

        odoo_id = odoo_client.execute_kw('drmoto.work.order', 'create', [odoo_payload])
        
        if not odoo_id:
            raise HTTPException(status_code=500, detail="Failed to create WO in Odoo")
            
        # Get the name generated by Odoo
        name = odoo_client.execute_kw('drmoto.work.order', 'read', [[odoo_id], ['name']])[0]['name']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Odoo create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create work order")

    # 2. Create in Local DB
    vehicle_key = _resolve_work_order_vehicle_key(db, customer_id, order_in.vehicle_plate)
    db_wo = WorkOrder(
        uuid=str(uuid.uuid4()),
        store_id=store_id,
        odoo_id=odoo_id,
        vehicle_plate=order_in.vehicle_plate,
        customer_id=str(order_in.customer_id),
        vehicle_key=vehicle_key,
        description=order_in.description,
        status="draft"
    )
    db.add(db_wo)
    db.commit()
    db.refresh(db_wo)
    _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=order_in.description)
    
    # 3. Update Odoo with BFF UUID (for callbacks)
    try:
        odoo_client.execute_kw('drmoto.work.order', 'write', [[odoo_id], {'bff_uuid': db_wo.uuid}])
    except:
        pass # Non-critical

    result = {
        "id": db_wo.uuid,
        "status": db_wo.status,
        "data": {
            "vehicle_plate": db_wo.vehicle_plate,
            "odoo_ref": name
        }
    }
    if idem_key:
        redis_client.setex(
            f"idempotency:wo:create:{store_id}:{idem_key}",
            settings.IDEMPOTENCY_TTL_SECONDS,
            json.dumps(result),
        )
    return result


@router.delete("/{order_id}")
async def delete_work_order(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    store_id = resolve_store_id(request, current_user)
    wo = _load_store_work_order(db, order_id, store_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    _delete_work_order(db, wo)
    db.commit()
    return {"deleted": 1, "order_id": order_id}


@router.post("/batch-delete")
async def batch_delete_work_orders(
    payload: WorkOrderBulkDeleteRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    store_id = resolve_store_id(request, current_user)
    success_order_ids = []
    failed_items = []
    for order_id in payload.order_ids:
        wo = _load_store_work_order(db, order_id, store_id)
        if not wo:
            failed_items.append({"order_id": order_id, "reason": "not_found"})
            continue
        try:
            _delete_work_order(db, wo)
            success_order_ids.append(order_id)
        except Exception as e:
            logger.error(f"Batch delete failed for {order_id}: {e}")
            failed_items.append({"order_id": order_id, "reason": "runtime_error"})
    db.commit()
    return {
        "requested": len(payload.order_ids),
        "succeeded": len(success_order_ids),
        "failed": len(failed_items),
        "success_order_ids": success_order_ids,
        "failed_items": failed_items,
    }

@router.get("/customers/{partner_id}/vehicles")
async def get_customer_vehicles(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Get vehicles for a specific customer."""
    try:
        # Search drmoto.partner.vehicle where partner_id = partner_id
        domain = [['partner_id', '=', partner_id]]
        fields = ['id', 'license_plate', 'vehicle_id', 'vin', 'color']
        try:
            vehicles = odoo_client.execute_kw('drmoto.partner.vehicle', 'search_read', [domain], {'fields': fields})
        except Exception as exc:
            if _is_odoo_model_missing_error(exc, "drmoto.partner.vehicle"):
                logger.warning("Odoo vehicle model is not installed; returning empty vehicles for partner_id=%s", partner_id)
                return []
            raise
        vehicle_model_ids = []
        for row in vehicles:
            ref = row.get("vehicle_id")
            if isinstance(ref, list) and ref:
                vid = ref[0]
                if vid not in vehicle_model_ids:
                    vehicle_model_ids.append(vid)
        model_map = {}
        if vehicle_model_ids:
            model_rows = odoo_client.execute_kw(
                "drmoto.vehicle",
                "read",
                [vehicle_model_ids, ["id", "make", "model", "year_from", "engine_code"]],
            )
            model_map = {row["id"]: row for row in model_rows}

        result = []
        for row in vehicles:
            ref = row.get("vehicle_id")
            vehicle_model_id = ref[0] if isinstance(ref, list) and ref else None
            vehicle_model = model_map.get(vehicle_model_id, {})
            make = normalize_text(vehicle_model.get("make"))
            model = normalize_text(vehicle_model.get("model"))
            year = vehicle_model.get("year_from") if isinstance(vehicle_model.get("year_from"), int) else None
            result.append({
                "id": row.get("id"),
                "partner_id": partner_id,
                "catalog_model_id": _find_catalog_model_id(
                    db,
                    make,
                    model,
                    year,
                    normalize_text(vehicle_model.get("engine_code")),
                ),
                "license_plate": normalize_text(row.get("license_plate")) or "",
                "vin": normalize_text(row.get("vin")),
                "color": normalize_text(row.get("color")),
                "vehicle_id": vehicle_model_id,
                "make": make,
                "model": model,
                "year": year,
                "engine_code": normalize_text(vehicle_model.get("engine_code")),
            })
        return result
    except Exception as e:
        logger.error(f"Vehicle fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch vehicles")


@router.get("/customers/with-vehicles", response_model=list[CustomerWithVehiclesResponse])
async def list_customers_with_vehicles(
    query: str = "",
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    try:
        normalized_query = compact_whitespace(query) or ""
        partner_domain = ['|', ['name', 'ilike', normalized_query], ['phone', 'ilike', normalized_query]] if normalized_query else []
        partner_fields = ["id", "name", "phone", "email"]
        partners = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [partner_domain],
            {"fields": partner_fields, "limit": limit, "order": "id desc"},
        )
        if not partners:
            return []

        partner_ids = [p["id"] for p in partners]
        vehicle_fields = ["id", "partner_id", "license_plate", "vin", "color", "vehicle_id"]
        try:
            vehicles = odoo_client.execute_kw(
                "drmoto.partner.vehicle",
                "search_read",
                [[["partner_id", "in", partner_ids]]],
                {"fields": vehicle_fields, "order": "id desc"},
            )
        except Exception as exc:
            if _is_odoo_model_missing_error(exc, "drmoto.partner.vehicle"):
                logger.warning("Odoo vehicle model is not installed; returning customers without vehicles")
                vehicles = []
            else:
                raise

        vehicle_model_ids = []
        for row in vehicles:
            vehicle_ref = row.get("vehicle_id")
            if isinstance(vehicle_ref, list) and vehicle_ref:
                vid = vehicle_ref[0]
                if vid not in vehicle_model_ids:
                    vehicle_model_ids.append(vid)
        vehicle_model_map = {}
        if vehicle_model_ids:
            vehicle_models = odoo_client.execute_kw(
                "drmoto.vehicle",
                "read",
                [vehicle_model_ids, ["id", "make", "model", "year_from", "engine_code"]],
            )
            vehicle_model_map = {row["id"]: row for row in vehicle_models}

        vehicles_by_partner = defaultdict(list)
        for row in vehicles:
            partner_ref = row.get("partner_id")
            partner_id = partner_ref[0] if isinstance(partner_ref, list) and partner_ref else None
            if not partner_id:
                continue
            vehicle_ref = row.get("vehicle_id")
            vehicle_model_id = vehicle_ref[0] if isinstance(vehicle_ref, list) and vehicle_ref else None
            vehicle_model = vehicle_model_map.get(vehicle_model_id, {})
            raw_plate = normalize_text(row.get("license_plate"))
            raw_vin = normalize_text(row.get("vin"))
            raw_color = normalize_text(row.get("color"))
            raw_make = normalize_text(vehicle_model.get("make"))
            raw_model = normalize_text(vehicle_model.get("model"))
            raw_engine_code = normalize_text(vehicle_model.get("engine_code"))
            raw_year = vehicle_model.get("year_from")
            normalized_year = int(raw_year) if isinstance(raw_year, int) and not isinstance(raw_year, bool) else None

            vehicles_by_partner[partner_id].append({
                "id": row["id"],
                "partner_id": partner_id,
                "catalog_model_id": _find_catalog_model_id(
                    db,
                    raw_make,
                    raw_model,
                    normalized_year,
                    raw_engine_code,
                ),
                "license_plate": raw_plate if isinstance(raw_plate, str) and raw_plate else "",
                "vin": raw_vin if isinstance(raw_vin, str) else None,
                "color": raw_color if isinstance(raw_color, str) else None,
                "vehicle_id": vehicle_model_id,
                "make": raw_make if isinstance(raw_make, str) else None,
                "model": raw_model if isinstance(raw_model, str) else None,
                "year": normalized_year,
                "engine_code": raw_engine_code if isinstance(raw_engine_code, str) else None,
            })

        result = []
        for partner in partners:
            items = vehicles_by_partner.get(partner["id"], [])
            raw_name = partner.get("name")
            raw_phone = partner.get("phone")
            raw_email = partner.get("email")
            result.append({
                "id": partner["id"],
                "name": normalize_text(raw_name) if isinstance(raw_name, str) else "",
                "phone": normalize_text(raw_phone) if isinstance(raw_phone, str) else None,
                "email": normalize_text(raw_email) if isinstance(raw_email, str) else None,
                "vehicle_count": len(items),
                "vehicles": items,
            })
        if normalized_query:
            result.sort(
                key=lambda item: (
                    _customer_match_score(normalized_query, item, item.get("vehicles") or []),
                    int(item.get("vehicle_count") or 0),
                    int(item.get("id") or 0),
                ),
                reverse=True,
            )
        return result
    except Exception as e:
        logger.error(f"Customer with vehicles list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customers with vehicles")

@router.get("/customers/{partner_id}/orders")
async def get_customer_orders(
    partner_id: int,
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Get work orders for a specific customer from Odoo."""
    try:
        domain = [['customer_id', '=', partner_id]]
        fields = ['id', 'name', 'vehicle_plate', 'state', 'date_planned', 'amount_total', 'bff_uuid']
        orders = odoo_client.execute_kw('drmoto.work.order', 'search_read', [domain], {'fields': fields, 'order': 'create_date desc'})
        return orders
    except Exception as e:
        logger.error(f"Customer orders fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/customers/{partner_id}/summary")
async def get_customer_summary(
    partner_id: int,
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"])),
):
    """Get customer value summary for CRM-style profile display."""
    try:
        partner_rows = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [[["id", "=", partner_id]]],
            {"fields": ["id", "name", "phone", "email"], "limit": 1},
        )
        if not partner_rows:
            raise HTTPException(status_code=404, detail="Customer not found")

        domain = [["customer_id", "=", partner_id]]
        fields = ["id", "state", "amount_total", "create_date", "date_planned"]
        orders = odoo_client.execute_kw(
            "drmoto.work.order",
            "search_read",
            [domain],
            {"fields": fields, "order": "create_date desc", "limit": 200},
        )

        total_orders = len(orders)
        done_orders = 0
        total_amount = 0.0
        last_visit_at = None
        for row in orders:
            state = normalize_text(row.get("state")) or ""
            if state == "done":
                done_orders += 1
            amount_val = row.get("amount_total")
            if isinstance(amount_val, (int, float)):
                total_amount += float(amount_val)
            dt_val = normalize_text(row.get("date_planned")) or normalize_text(row.get("create_date"))
            if dt_val and (last_visit_at is None or dt_val > last_visit_at):
                last_visit_at = dt_val

        return {
            "customer_id": partner_id,
            "total_orders": total_orders,
            "done_orders": done_orders,
            "completion_rate": (done_orders / total_orders) if total_orders else 0,
            "total_amount": round(total_amount, 2),
            "last_visit_at": last_visit_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer summary fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer summary")


@router.post("/customers/{partner_id}/vehicles/{license_plate}/health-records", response_model=VehicleHealthRecordResponse)
async def create_vehicle_health_record(
    partner_id: int,
    license_plate: str,
    payload: VehicleHealthRecordCreate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    plate = compact_whitespace(license_plate)
    if not plate:
        raise HTTPException(status_code=400, detail="license_plate is required")

    measured_at = payload.measured_at or datetime.now(timezone.utc)
    row = VehicleHealthRecord(
        store_id=store_id,
        customer_id=str(partner_id),
        vehicle_plate=plate,
        measured_at=measured_at,
        odometer_km=payload.odometer_km,
        engine_rpm=payload.engine_rpm,
        battery_voltage=payload.battery_voltage,
        tire_front_psi=payload.tire_front_psi,
        tire_rear_psi=payload.tire_rear_psi,
        coolant_temp_c=payload.coolant_temp_c,
        oil_life_percent=payload.oil_life_percent,
        notes=payload.notes,
        extra_json=payload.extra,
        created_by=current_user.username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    prev = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == str(partner_id),
            VehicleHealthRecord.vehicle_plate == plate,
            VehicleHealthRecord.id != row.id,
            VehicleHealthRecord.measured_at <= row.measured_at,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    return _to_health_response(row, prev)


@router.get("/customers/{partner_id}/vehicles/{license_plate}/health-records", response_model=list[VehicleHealthRecordResponse])
async def list_vehicle_health_records(
    partner_id: int,
    license_plate: str,
    limit: int = Query(100, ge=1, le=500),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"])),
):
    store_id = resolve_store_id(request, current_user)
    plate = compact_whitespace(license_plate)
    if not plate:
        raise HTTPException(status_code=400, detail="license_plate is required")

    rows = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == str(partner_id),
            VehicleHealthRecord.vehicle_plate == plate,
        )
        .order_by(VehicleHealthRecord.measured_at.asc(), VehicleHealthRecord.id.asc())
        .limit(limit)
        .all()
    )
    result = []
    prev = None
    for row in rows:
        result.append(_to_health_response(row, prev))
        prev = row
    return result

@router.get("/search", response_model=list)
async def search_work_orders(
    plate: str = Query(..., min_length=1, max_length=32),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    db_wos = (
        db.query(WorkOrder)
        .filter(WorkOrder.vehicle_plate == plate, WorkOrder.store_id == store_id)
        .all()
    )
    results = []
    for wo in db_wos:
        results.append({
            "id": wo.uuid,
            "status": wo.status,
            "data": {
                "vehicle_plate": wo.vehicle_plate,
                "description": wo.description,
                "customer_id": wo.customer_id
            }
        })
    return results


@router.get("/search/page", response_model=dict)
async def search_work_orders_page(
    plate: str = Query("", max_length=32),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    query = db.query(WorkOrder).filter(WorkOrder.store_id == store_id)
    if plate:
        query = query.filter(WorkOrder.vehicle_plate.ilike(f"%{plate}%"))
        candidates = query.all()
        ranked = sorted(
            candidates,
            key=lambda row: (_plate_match_score(plate, row.vehicle_plate), row.created_at.isoformat() if row.created_at else ""),
            reverse=True,
        )
        total = len(ranked)
        offset = (page - 1) * size
        db_wos = ranked[offset:offset + size]
    else:
        total = query.count()
        offset = (page - 1) * size
        db_wos = query.order_by(WorkOrder.created_at.desc()).offset(offset).limit(size).all()

    items = []
    for wo in db_wos:
        process_row = (
            db.query(WorkOrderProcessRecord)
            .filter(
                WorkOrderProcessRecord.store_id == store_id,
                WorkOrderProcessRecord.work_order_uuid == wo.uuid,
            )
            .first()
        )
        process_data = _process_record_to_response(wo.uuid, process_row)
        advanced_row = (
            db.query(WorkOrderAdvancedProfile)
            .filter(
                WorkOrderAdvancedProfile.store_id == store_id,
                WorkOrderAdvancedProfile.work_order_uuid == wo.uuid,
            )
            .first()
        )
        advanced_data = _advanced_profile_to_response(advanced_row)
        items.append({
            "id": wo.uuid,
            "status": wo.status,
            "vehicle_plate": wo.vehicle_plate,
            "description": wo.description,
            "symptom_draft": process_data.get("symptom_draft"),
            "symptom_confirmed": process_data.get("symptom_confirmed"),
            "quick_check": process_data.get("quick_check"),
            "customer_id": wo.customer_id,
            "created_at": wo.created_at.isoformat() if wo.created_at else None,
            "priority": advanced_data.get("priority"),
            "is_urgent": advanced_data.get("is_urgent"),
            "is_rework": advanced_data.get("is_rework"),
            "assigned_technician": advanced_data.get("assigned_technician"),
            "service_bay": advanced_data.get("service_bay"),
            "estimated_finish_at": advanced_data.get("estimated_finish_at"),
        })

    return {
        "items": items,
        "page": page,
        "size": size,
        "total": total,
        "has_more": (offset + len(items)) < total,
    }


@router.get("/list/page", response_model=dict)
async def list_work_orders_page(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query("", max_length=32),
    status_group: str = Query("", max_length=32),
    customer_id: str = Query("", max_length=64),
    plate: str = Query("", max_length=32),
    created_from: str = Query("", description="ISO datetime, e.g. 2026-03-29T00:00:00+08:00"),
    created_to: str = Query("", description="ISO datetime"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    query = db.query(WorkOrder).filter(WorkOrder.store_id == store_id)

    normalized_group = (status_group or "").strip().lower()
    if normalized_group == "active":
        query = query.filter(WorkOrder.status.notin_(["done", "cancel"]))
    elif normalized_group == "frontdesk_todo":
        query = query.filter(WorkOrder.status.in_(["draft", "confirmed", "quoted", "ready"]))
    elif normalized_group == "workshop":
        query = query.filter(WorkOrder.status.in_(["diagnosing", "in_progress"]))
    elif normalized_group == "closed":
        query = query.filter(WorkOrder.status.in_(["done", "cancel"]))

    if status:
        query = query.filter(WorkOrder.status == status)
    if customer_id:
        query = query.filter(WorkOrder.customer_id == customer_id)
    if plate:
        query = query.filter(WorkOrder.vehicle_plate.ilike(f"%{plate}%"))

    from_dt = _parse_iso_datetime(created_from)
    to_dt = _parse_iso_datetime(created_to)
    if from_dt:
        query = query.filter(WorkOrder.created_at >= from_dt)
    if to_dt:
        query = query.filter(WorkOrder.created_at <= to_dt)

    if plate:
        candidates = query.all()
        ranked = sorted(
            candidates,
            key=lambda row: (_plate_match_score(plate, row.vehicle_plate), row.created_at.isoformat() if row.created_at else ""),
            reverse=True,
        )
        total = len(ranked)
        offset = (page - 1) * size
        rows = ranked[offset:offset + size]
    else:
        total = query.count()
        offset = (page - 1) * size
        rows = query.order_by(WorkOrder.created_at.desc()).offset(offset).limit(size).all()

    items = []
    for wo in rows:
        process_row = (
            db.query(WorkOrderProcessRecord)
            .filter(
                WorkOrderProcessRecord.store_id == store_id,
                WorkOrderProcessRecord.work_order_uuid == wo.uuid,
            )
            .first()
        )
        process_data = _process_record_to_response(wo.uuid, process_row)
        advanced_row = (
            db.query(WorkOrderAdvancedProfile)
            .filter(
                WorkOrderAdvancedProfile.store_id == store_id,
                WorkOrderAdvancedProfile.work_order_uuid == wo.uuid,
            )
            .first()
        )
        advanced_data = _advanced_profile_to_response(advanced_row)
        items.append({
            "id": wo.uuid,
            "status": wo.status,
            "vehicle_plate": wo.vehicle_plate,
            "customer_id": wo.customer_id,
            "description": wo.description,
            "symptom_draft": process_data.get("symptom_draft"),
            "symptom_confirmed": process_data.get("symptom_confirmed"),
            "quick_check": process_data.get("quick_check"),
            "active_quote_version": wo.active_quote_version,
            "created_at": wo.created_at.isoformat() if wo.created_at else None,
            "priority": advanced_data.get("priority"),
            "is_urgent": advanced_data.get("is_urgent"),
            "is_rework": advanced_data.get("is_rework"),
            "assigned_technician": advanced_data.get("assigned_technician"),
            "service_bay": advanced_data.get("service_bay"),
            "estimated_finish_at": advanced_data.get("estimated_finish_at"),
        })

    return {
        "items": items,
        "page": page,
        "size": size,
        "total": total,
        "has_more": (offset + len(items)) < total,
        "filters": {
            "status": status,
            "status_group": normalized_group,
            "customer_id": customer_id,
            "plate": plate,
            "created_from": created_from,
            "created_to": created_to,
        },
    }

def _load_order_snapshot(db: Session, order_id: str, store_id: str):
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    # Fetch details from Odoo if possible
    odoo_details = {}
    if db_wo.odoo_id:
        try:
            fields = ['name', 'state', 'line_ids', 'amount_total', 'procedure_id']
            data = odoo_client.execute_kw('drmoto.work.order', 'read', [[db_wo.odoo_id], fields])
            if data:
                odoo_details = data[0]
                # If we have lines, fetch line details
                if odoo_details.get('line_ids'):
                    line_fields = ['product_id', 'name', 'quantity', 'price_unit', 'price_subtotal']
                    lines = odoo_client.execute_kw('drmoto.work.order.line', 'read', [odoo_details['line_ids'], line_fields])
                    odoo_details['lines'] = lines
        except Exception as e:
            logger.error(f"Failed to fetch Odoo details: {e}")

    return db_wo, odoo_details


@router.get("/{order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    db_wo, odoo_details = _load_order_snapshot(db, order_id, store_id)
    process_row = _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=db_wo.description)
    process_data = _process_record_to_response(db_wo.uuid, process_row)
    delivery_row = _ensure_delivery_checklist(db, store_id, db_wo.uuid)
    advanced_row = _ensure_advanced_profile(db, store_id, db_wo.uuid)

    return {
        "id": db_wo.uuid,
        "status": odoo_details.get('state', db_wo.status), # Prefer Odoo status
        "data": {
            "vehicle_plate": db_wo.vehicle_plate,
            "description": db_wo.description,
            "customer_id": db_wo.customer_id,
            "created_at": db_wo.created_at.isoformat() if db_wo.created_at else None,
            "process_record": process_data,
            "delivery_checklist": _delivery_checklist_to_response(delivery_row, db, store_id),
            "advanced_profile": _advanced_profile_to_response(advanced_row),
            "odoo": odoo_details
        }
    }


@router.get("/{order_id}/service-plan", response_model=dict)
async def get_work_order_service_plan(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    customer_id_int = _parse_positive_int(db_wo.customer_id)
    vehicle_row = {}
    try:
        partner_vehicle_domain = [["license_plate", "=", db_wo.vehicle_plate]]
        if customer_id_int is not None:
            partner_vehicle_domain.append(["partner_id", "=", customer_id_int])
        partner_vehicle_rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [partner_vehicle_domain],
            {"fields": ["id", "license_plate", "vehicle_id", "vin", "color"], "limit": 1},
        )
        partner_vehicle = partner_vehicle_rows[0] if partner_vehicle_rows else {}
        vehicle_ref = partner_vehicle.get("vehicle_id")
        vehicle_model_id = vehicle_ref[0] if isinstance(vehicle_ref, list) and vehicle_ref else None
        vehicle_model = {}
        if vehicle_model_id:
            model_rows = odoo_client.execute_kw(
                "drmoto.vehicle",
                "read",
                [[vehicle_model_id], ["id", "make", "model", "year_from", "engine_code"]],
            )
            vehicle_model = model_rows[0] if model_rows else {}
        vehicle_row = {
            "plate_number": partner_vehicle.get("license_plate") or db_wo.vehicle_plate,
            "vehicle_plate": partner_vehicle.get("license_plate") or db_wo.vehicle_plate,
            "vin": partner_vehicle.get("vin"),
            "color": partner_vehicle.get("color"),
            "make": vehicle_model.get("make"),
            "model": vehicle_model.get("model"),
            "year": vehicle_model.get("year_from"),
            "engine_code": vehicle_model.get("engine_code"),
        }
    except Exception as exc:
        logger.warning("Service plan vehicle lookup fallback for %s: %s", order_id, exc)
    catalog_model_id = _extract_odoo_many2one_id(vehicle_row.get("catalog_model_id"))
    if not catalog_model_id:
        catalog_model_id = _find_catalog_model_id(
            db,
            vehicle_row.get("make"),
            vehicle_row.get("model"),
            vehicle_row.get("year"),
            vehicle_row.get("engine_code"),
        )
    vehicle_row["catalog_model_id"] = catalog_model_id
    catalog_model = None
    standard_items: list[dict] = []
    if catalog_model_id:
        catalog_model = (
            db.query(VehicleCatalogModel)
            .filter(
                VehicleCatalogModel.id == catalog_model_id,
                VehicleCatalogModel.is_active.is_(True),
            )
            .first()
        )
    if not catalog_model:
        fallback_catalog_id = _find_catalog_model_id(
            db,
            vehicle_row.get("make"),
            vehicle_row.get("model"),
            vehicle_row.get("year"),
            vehicle_row.get("engine_code"),
        )
        if fallback_catalog_id:
            catalog_model_id = fallback_catalog_id
            vehicle_row["catalog_model_id"] = fallback_catalog_id
            catalog_model = (
                db.query(VehicleCatalogModel)
                .filter(
                    VehicleCatalogModel.id == fallback_catalog_id,
                    VehicleCatalogModel.is_active.is_(True),
                )
                .first()
            )
    if catalog_model:
        template_rows = (
            db.query(VehicleServiceTemplateItem)
            .filter(
                VehicleServiceTemplateItem.model_id == catalog_model.id,
                VehicleServiceTemplateItem.is_active.is_(True),
            )
            .order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc())
            .all()
        )
        template_ids = [row.id for row in template_rows]
        profile_map = {
            row.template_item_id: row
            for row in db.query(VehicleServiceTemplateProfile).filter(
                VehicleServiceTemplateProfile.template_item_id.in_(template_ids or [-1])
            ).all()
        }
        parts_map = _serialize_template_required_parts(db, template_ids)
        standard_items = [
            _service_template_to_dict(row, profile_map.get(row.id), parts_map.get(row.id, []))
            for row in template_rows
        ]

    selected_rows = (
        db.query(WorkOrderServiceSelection)
        .filter(
            WorkOrderServiceSelection.store_id == store_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
        )
        .order_by(WorkOrderServiceSelection.sort_order.asc(), WorkOrderServiceSelection.id.asc())
        .all()
    )
    if not catalog_model:
        selected_template_ids = [row.template_item_id for row in selected_rows if row.template_item_id]
        if selected_template_ids:
            inferred_model_ids = {
                row[0]
                for row in db.query(VehicleServiceTemplateItem.model_id)
                .filter(VehicleServiceTemplateItem.id.in_(selected_template_ids))
                .all()
                if row and row[0]
            }
            if len(inferred_model_ids) == 1:
                inferred_model_id = next(iter(inferred_model_ids))
                catalog_model = (
                    db.query(VehicleCatalogModel)
                    .filter(
                        VehicleCatalogModel.id == inferred_model_id,
                        VehicleCatalogModel.is_active.is_(True),
                    )
                    .first()
                )
                if catalog_model:
                    catalog_model_id = catalog_model.id
                    vehicle_row["catalog_model_id"] = catalog_model.id
                    vehicle_row.setdefault("make", catalog_model.brand)
                    vehicle_row.setdefault("model", catalog_model.model_name)
                    vehicle_row.setdefault("year", catalog_model.year_from)
                    vehicle_row.setdefault("engine_code", catalog_model.default_engine_code)
    selected_items = [_service_selection_to_dict(row) for row in selected_rows]
    service_packages = (
        _serialize_service_packages_for_work_order(
            db,
            catalog_model.id,
            {row.template_item_id for row in selected_rows if row.template_item_id},
        )
        if catalog_model
        else []
    )
    totals = {
        "parts_total": round(sum(item["parts_total"] for item in selected_items), 2),
        "labor_total": round(sum(float(item["labor_price"] or 0) for item in selected_items), 2),
        "grand_total": round(sum(item["line_total"] for item in selected_items), 2),
    }
    quote_summary = _get_work_order_quote_summary(db, store_id, order_id, db_wo.active_quote_version)
    quote_rows = quote_summary["rows"]
    latest_quote = quote_summary["latest"]
    active_quote = quote_summary["active"]
    workflow_checks = _build_work_order_workflow_checks(db, store_id, db_wo, selected_items=selected_items)
    return {
        "order_id": order_id,
        "catalog_model": {
            "id": catalog_model.id,
            "brand": catalog_model.brand,
            "model_name": catalog_model.model_name,
            "year_from": catalog_model.year_from,
            "year_to": catalog_model.year_to,
        } if catalog_model else None,
        "vehicle": vehicle_row,
        "standard_items": standard_items,
        "service_packages": service_packages,
        "selected_items": selected_items,
        "totals": totals,
        "quote_summary": {
            "active_version": db_wo.active_quote_version,
            "latest": {
                "version": latest_quote.version,
                "status": latest_quote.status,
                "is_active": bool(latest_quote.is_active),
                "amount_total": latest_quote.amount_total,
                "created_at": latest_quote.created_at.isoformat() if latest_quote.created_at else None,
            } if latest_quote else None,
            "active": {
                "version": active_quote.version,
                "status": active_quote.status,
                "is_active": bool(active_quote.is_active),
                "amount_total": active_quote.amount_total,
                "created_at": active_quote.created_at.isoformat() if active_quote.created_at else None,
            } if active_quote else None,
            "versions": [
                {
                    "version": row.version,
                    "status": row.status,
                    "is_active": bool(row.is_active),
                    "amount_total": row.amount_total,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in quote_rows[:5]
            ],
        },
        "workflow_checks": workflow_checks,
    }


@router.post("/{order_id}/service-selections", response_model=dict)
async def add_work_order_service_selection(
    order_id: str,
    payload: dict,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    template_item_id = payload.get("template_item_id")
    if template_item_id is None:
        raise HTTPException(status_code=400, detail="template_item_id is required")
    template_item_id = _require_positive_int(template_item_id, "template_item_id")

    template_row = db.query(VehicleServiceTemplateItem).filter(VehicleServiceTemplateItem.id == template_item_id).first()
    if not template_row:
        raise HTTPException(status_code=404, detail="Service template not found")

    exists = (
        db.query(WorkOrderServiceSelection.id)
        .filter(
            WorkOrderServiceSelection.store_id == store_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
            WorkOrderServiceSelection.template_item_id == template_item_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Service item already selected")

    profile = (
        db.query(VehicleServiceTemplateProfile)
        .filter(VehicleServiceTemplateProfile.template_item_id == template_item_id)
        .first()
    )
    required_parts = _serialize_template_required_parts(db, [template_item_id]).get(template_item_id, [])
    selection = WorkOrderServiceSelection(
        store_id=store_id,
        work_order_uuid=order_id,
        template_item_id=template_item_id,
        service_name=template_row.part_name,
        service_code=template_row.part_code,
        repair_method=template_row.repair_method,
        labor_hours=template_row.labor_hours,
        labor_price=profile.labor_price if profile and profile.labor_price is not None else 0,
        suggested_price=(
            profile.suggested_price
            if profile and profile.suggested_price is not None
            else round(sum(float(item.get("qty") or 0) * float(item.get("unit_price") or 0) for item in required_parts), 2)
        ),
        notes=template_row.notes,
        required_parts_json=required_parts,
        sort_order=template_row.sort_order,
        created_by=current_user.username,
    )
    db.add(selection)
    db.commit()
    db.refresh(selection)
    return _service_selection_to_dict(selection)


@router.post("/{order_id}/service-packages/{package_id}/apply", response_model=dict)
async def apply_work_order_service_package(
    order_id: str,
    package_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    package_row = (
        db.query(VehicleServicePackage)
        .filter(
            VehicleServicePackage.id == package_id,
            VehicleServicePackage.is_active.is_(True),
        )
        .first()
    )
    if not package_row:
        raise HTTPException(status_code=404, detail="Service package not found")

    package_items = (
        db.query(VehicleServicePackageItem)
        .filter(VehicleServicePackageItem.package_id == package_id)
        .order_by(VehicleServicePackageItem.sort_order.asc(), VehicleServicePackageItem.id.asc())
        .all()
    )
    if not package_items:
        raise HTTPException(status_code=400, detail="Service package has no items")

    existing_rows = _load_work_order_service_selections(db, store_id, order_id)
    existing_template_ids = {
        int(row.template_item_id)
        for row in existing_rows
        if row.template_item_id
    }
    next_sort_order = max([int(row.sort_order or 0) for row in existing_rows] + [0]) + 10

    added_items: list[dict] = []
    skipped_template_ids: list[int] = []
    template_ids = [row.template_item_id for row in package_items]
    template_rows = {
        row.id: row
        for row in db.query(VehicleServiceTemplateItem).filter(
            VehicleServiceTemplateItem.id.in_(template_ids or [-1])
        ).all()
    }
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile).filter(
            VehicleServiceTemplateProfile.template_item_id.in_(template_ids or [-1])
        ).all()
    }
    required_parts_map = _serialize_template_required_parts(db, template_ids)

    for package_item in package_items:
        template_item_id = int(package_item.template_item_id)
        if template_item_id in existing_template_ids:
            skipped_template_ids.append(template_item_id)
            continue
        template_row = template_rows.get(template_item_id)
        if not template_row:
            continue
        profile = profile_map.get(template_item_id)
        required_parts = required_parts_map.get(template_item_id, [])
        selection = WorkOrderServiceSelection(
            store_id=store_id,
            work_order_uuid=order_id,
            template_item_id=template_item_id,
            service_name=template_row.part_name,
            service_code=template_row.part_code,
            repair_method=template_row.repair_method,
            labor_hours=template_row.labor_hours,
            labor_price=profile.labor_price if profile and profile.labor_price is not None else 0,
            suggested_price=(
                profile.suggested_price
                if profile and profile.suggested_price is not None
                else round(sum(float(item.get("qty") or 0) * float(item.get("unit_price") or 0) for item in required_parts), 2)
            ),
            notes=normalize_text(package_item.notes) or template_row.notes,
            required_parts_json=required_parts,
            sort_order=next_sort_order,
            created_by=current_user.username,
        )
        next_sort_order += 10
        db.add(selection)
        db.flush()
        added_items.append(_service_selection_to_dict(selection))
        existing_template_ids.add(template_item_id)

    db.commit()
    return {
        "order_id": order_id,
        "package_id": package_id,
        "package_name": package_row.package_name,
        "added_count": len(added_items),
        "skipped_count": len(skipped_template_ids),
        "added_items": added_items,
        "skipped_template_item_ids": skipped_template_ids,
    }


@router.delete("/{order_id}/service-selections/{selection_id}")
async def delete_work_order_service_selection(
    order_id: str,
    selection_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    row = (
        db.query(WorkOrderServiceSelection)
        .filter(
            WorkOrderServiceSelection.id == selection_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
            WorkOrderServiceSelection.store_id == store_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Selected service item not found")
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": selection_id}


@router.put("/{order_id}/service-selections/{selection_id}", response_model=dict)
async def update_work_order_service_selection(
    order_id: str,
    selection_id: int,
    payload: WorkOrderServiceSelectionUpdate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    row = (
        db.query(WorkOrderServiceSelection)
        .filter(
            WorkOrderServiceSelection.id == selection_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
            WorkOrderServiceSelection.store_id == store_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Selected service item not found")

    if payload.labor_price is not None:
        if payload.labor_price < 0:
            raise HTTPException(status_code=400, detail="labor_price must be >= 0")
        row.labor_price = round(float(payload.labor_price), 2)
    if payload.suggested_price is not None:
        if payload.suggested_price < 0:
            raise HTTPException(status_code=400, detail="suggested_price must be >= 0")
        row.suggested_price = round(float(payload.suggested_price), 2)
    if payload.notes is not None:
        row.notes = normalize_text(payload.notes)
    db.commit()
    db.refresh(row)
    return _service_selection_to_dict(row)


@router.put("/{order_id}/service-selections/reorder", response_model=dict)
async def reorder_work_order_service_selections(
    order_id: str,
    payload: WorkOrderServiceSelectionReorderRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    rows = _load_work_order_service_selections(db, store_id, order_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No selected service items")

    row_map = {row.id: row for row in rows}
    current_ids = [row.id for row in rows]
    normalized_ids: list[int] = []
    for selection_id in payload.selection_ids:
        if selection_id not in row_map:
            raise HTTPException(status_code=404, detail=f"Selected service item not found: {selection_id}")
        if selection_id not in normalized_ids:
            normalized_ids.append(selection_id)
    for selection_id in current_ids:
        if selection_id not in normalized_ids:
            normalized_ids.append(selection_id)

    for index, selection_id in enumerate(normalized_ids, start=1):
        row_map[selection_id].sort_order = index * 10
    db.commit()
    return {
        "order_id": order_id,
        "selection_ids": normalized_ids,
    }


@router.post("/{order_id}/service-plan/generate-quote", response_model=dict)
async def generate_quote_from_service_plan(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    selections = (
        db.query(WorkOrderServiceSelection)
        .filter(
            WorkOrderServiceSelection.store_id == store_id,
            WorkOrderServiceSelection.work_order_uuid == order_id,
        )
        .order_by(WorkOrderServiceSelection.sort_order.asc(), WorkOrderServiceSelection.id.asc())
        .all()
    )
    if not selections:
        raise HTTPException(status_code=400, detail="No selected service items")

    latest = (
        db.query(Quote)
        .filter(Quote.work_order_uuid == order_id, Quote.store_id == store_id)
        .order_by(Quote.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1
    items: list[dict] = []
    for selection in selections:
        data = _service_selection_to_dict(selection)
        for part in data["required_parts"]:
            items.append(
                {
                    "item_type": "part",
                    "code": part.get("part_no"),
                    "name": part.get("part_name"),
                    "qty": _to_float(part.get("qty"), 0.0),
                    "unit_price": _to_float(part.get("unit_price"), 0.0),
                }
            )
        items.append(
            {
                "item_type": "labor",
                "code": data.get("service_code"),
                "name": f"{data['service_name']}工时费",
                "qty": 1,
                "unit_price": _to_float(data.get("labor_price"), 0.0),
            }
        )
    amount_total = round(sum(_to_float(item.get("qty"), 0.0) * _to_float(item.get("unit_price"), 0.0) for item in items), 2)
    quote = Quote(
        store_id=store_id,
        work_order_uuid=order_id,
        version=version,
        items_json=items,
        amount_total=amount_total,
        is_active=False,
        status="draft",
        created_by=current_user.username,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return {"work_order_id": order_id, "version": version, "amount_total": amount_total, "items": items}


@router.get("/{order_id}/delivery-checklist", response_model=dict)
async def get_work_order_delivery_checklist(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    row = _ensure_delivery_checklist(db, store_id, db_wo.uuid)
    return _delivery_checklist_to_response(row, db, store_id)


@router.put("/{order_id}/delivery-checklist", response_model=dict)
async def update_work_order_delivery_checklist(
    order_id: str,
    payload: dict,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    row = _ensure_delivery_checklist(db, store_id, db_wo.uuid)
    base = _default_delivery_checklist(db, store_id)
    merged = {**base, **(payload or {})}
    row.explained_to_customer = bool(merged.get("explained_to_customer"))
    row.returned_old_parts = bool(merged.get("returned_old_parts"))
    row.next_service_notified = bool(merged.get("next_service_notified"))
    row.payment_confirmed = bool(merged.get("payment_confirmed"))
    row.payment_method = normalize_text(merged.get("payment_method"))
    amount = merged.get("payment_amount")
    if amount in (None, ""):
        row.payment_amount = None
    else:
        try:
            row.payment_amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="payment_amount must be a valid number") from exc
    row.notes = normalize_text(merged.get("notes"))
    row.updated_by = current_user.username
    db.commit()
    db.refresh(row)
    return _delivery_checklist_to_response(row, db, store_id)


@router.get("/{order_id}/advanced-profile", response_model=dict)
async def get_work_order_advanced_profile(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    row = _ensure_advanced_profile(db, store_id, db_wo.uuid)
    return _advanced_profile_to_response(row)


@router.put("/{order_id}/advanced-profile", response_model=dict)
async def update_work_order_advanced_profile(
    order_id: str,
    payload: dict,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    row = _ensure_advanced_profile(db, store_id, db_wo.uuid)
    merged = {**_default_advanced_profile(), **(payload or {})}
    row.assigned_technician = normalize_text(merged.get("assigned_technician"))
    row.service_bay = normalize_text(merged.get("service_bay"))
    row.priority = normalize_text(merged.get("priority")) or "normal"
    row.promised_at = _parse_iso_datetime(merged.get("promised_at"))
    row.estimated_finish_at = _parse_iso_datetime(merged.get("estimated_finish_at"))
    row.is_rework = bool(merged.get("is_rework"))
    row.is_urgent = bool(merged.get("is_urgent"))
    row.qc_owner = normalize_text(merged.get("qc_owner"))
    row.internal_notes = normalize_text(merged.get("internal_notes"))
    row.updated_by = current_user.username
    db.commit()
    db.refresh(row)
    return _advanced_profile_to_response(row)


@router.get("/{order_id}/process-record", response_model=WorkOrderProcessRecordResponse)
async def get_work_order_process_record(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    row = _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=db_wo.description)
    return _process_record_to_response(db_wo.uuid, row)


@router.put("/{order_id}/process-record", response_model=WorkOrderProcessRecordResponse)
async def update_work_order_process_record(
    order_id: str,
    payload: WorkOrderProcessRecordUpdate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    row = _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=db_wo.description)

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "symptom_draft" in patch:
        row.symptom_draft = patch["symptom_draft"]
        if patch["symptom_draft"]:
            db_wo.description = patch["symptom_draft"]
    if "symptom_confirmed" in patch:
        row.symptom_confirmed = patch["symptom_confirmed"]
    if "quick_check" in patch:
        current_quick = row.quick_check_json if isinstance(row.quick_check_json, dict) else _default_quick_check()
        new_quick = patch["quick_check"] if isinstance(patch["quick_check"], dict) else {}
        merged = {**current_quick, **new_quick}
        row.quick_check_json = merged

    db.commit()
    db.refresh(row)
    return _process_record_to_response(db_wo.uuid, row)

from ..core.audit import log_audit
from ..integrations.mq import event_bus

@router.post("/{order_id}/status")
async def update_status(
    order_id: str,
    status: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Update status in Odoo (and local)."""
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    current = db_wo.status
    allowed_next = WORK_ORDER_TRANSITIONS.get(current, set())
    if status not in allowed_next:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid status transition: {current} -> {status}. Allowed: {sorted(allowed_next)}"
        )
    _validate_transition_prerequisites(db, store_id, db_wo, status)

    try:
        # Audit Log (Before)
        before_state = {"status": db_wo.status}

        if db_wo.odoo_id:
            try:
                # We write to Odoo, and let webhook sync back OR sync manually here
                odoo_client.execute_kw('drmoto.work.order', 'write', [[db_wo.odoo_id], {'state': status}])
            except Exception as e:
                if _is_odoo_record_missing_error(e):
                    logger.warning(f"Odoo work order missing, fallback to local status update only: {order_id}, odoo_id={db_wo.odoo_id}")
                    db_wo.odoo_id = None
                else:
                    raise

        # Manually sync local just in case
        db_wo.status = status
        db.commit()
        
        # Audit Log (After)
        log_audit(
            db,
            actor_id=current_user.id if hasattr(current_user, 'id') else 'system',
            action="update_status",
            target=f"work_order:{order_id}",
            before=before_state,
            after={"status": status},
            store_id=store_id,
        )
        
        # Publish Domain Event
        event_bus.publish("evt:work_order_updated", {"id": order_id, "status": status, "user": str(current_user)})

        return {"status": "success", "new_state": status}
    except HTTPException:
         raise
    except Exception as e:
         logger.error(f"Status update failed: {e}")
         raise HTTPException(status_code=500, detail="Failed to update status")


@router.post("/bulk/update-status", response_model=WorkOrderBulkStatusResult)
async def bulk_update_status(
    payload: WorkOrderBulkStatusUpdate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    store_id = resolve_store_id(request, current_user)
    target_status = compact_whitespace(payload.target_status).lower()
    if not target_status:
        raise HTTPException(status_code=400, detail="target_status is required")

    order_ids = []
    for oid in payload.order_ids:
        n = compact_whitespace(oid)
        if n and n not in order_ids:
            order_ids.append(n)
    if not order_ids:
        raise HTTPException(status_code=400, detail="order_ids is required")

    validation_errors = []
    orders = []
    for oid in order_ids:
        wo = _load_store_work_order(db, oid, store_id)
        if not wo:
            validation_errors.append({"order_id": oid, "reason": "not_found"})
            continue
        allowed_next = WORK_ORDER_TRANSITIONS.get(wo.status or "draft", set())
        if target_status not in allowed_next:
            validation_errors.append({
                "order_id": oid,
                "reason": "invalid_transition",
                "current_status": wo.status,
                "allowed_next": sorted(list(allowed_next)),
            })
            continue
        workflow_checks = _build_work_order_workflow_checks(db, store_id, wo)
        gate = workflow_checks["gates"].get(target_status, {"ready": True, "missing": []})
        if not gate["ready"]:
            validation_errors.append({
                "order_id": oid,
                "reason": "missing_prerequisites",
                "current_status": wo.status,
                "target_status": target_status,
                "missing": gate["missing"],
            })
            continue
        orders.append(wo)

    if validation_errors and payload.strict:
        return WorkOrderBulkStatusResult(
            requested=len(order_ids),
            succeeded=0,
            failed=len(validation_errors),
            target_status=target_status,
            success_order_ids=[],
            failed_items=validation_errors,
        )

    success_ids = []
    failed_items = list(validation_errors)
    for wo in orders:
        try:
            before_state = {"status": wo.status}
            if wo.odoo_id:
                try:
                    odoo_client.execute_kw('drmoto.work.order', 'write', [[wo.odoo_id], {'state': target_status}])
                except Exception as e:
                    if _is_odoo_record_missing_error(e):
                        logger.warning(f"Odoo work order missing in bulk update, fallback to local only: {wo.uuid}, odoo_id={wo.odoo_id}")
                        wo.odoo_id = None
                    else:
                        raise
            wo.status = target_status
            db.commit()
            success_ids.append(wo.uuid)
            log_audit(
                db,
                actor_id=current_user.username,
                action="bulk_update_status",
                target=f"work_order:{wo.uuid}",
                before=before_state,
                after={"status": target_status},
                store_id=store_id,
            )
            event_bus.publish("evt:work_order_updated", {"id": wo.uuid, "status": target_status, "user": current_user.username})
        except Exception as e:
            db.rollback()
            logger.error(f"Bulk status update failed for {wo.uuid}: {e}")
            failed_items.append({"order_id": wo.uuid, "reason": "runtime_error"})
            if payload.strict:
                break

    return WorkOrderBulkStatusResult(
        requested=len(order_ids),
        succeeded=len(success_ids),
        failed=len(failed_items),
        target_status=target_status,
        success_order_ids=success_ids,
        failed_items=failed_items,
    )


@router.get("/{order_id}/actions", response_model=dict)
async def get_work_order_actions(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    db_wo, odoo_details = _load_order_snapshot(db, order_id, store_id)
    current = odoo_details.get("state") or db_wo.status or "draft"
    next_statuses = sorted(list(WORK_ORDER_TRANSITIONS.get(current, set())))
    actions = []
    for s in next_statuses:
        actions.append({"to_status": s, "action": STATUS_ACTION_LABELS.get(s, s)})
    return {"order_id": order_id, "current_status": current, "actions": actions}


@router.get("/{order_id}/timeline", response_model=list)
async def get_work_order_timeline(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    db_wo = _load_store_work_order(db, order_id, store_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    target = f"work_order:{order_id}"
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.target_entity == target, AuditLog.store_id == store_id)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        .all()
    )

    timeline = [{
        "time": db_wo.created_at.isoformat() if db_wo.created_at else None,
        "actor": "system",
        "action": "create_work_order",
        "before": None,
        "after": {"status": db_wo.status},
    }]

    for log in logs:
        timeline.append({
            "time": log.created_at.isoformat() if log.created_at else None,
            "actor": log.actor_id,
            "action": log.action,
            "before": log.before_state,
            "after": log.after_state,
        })
    return timeline

def _fetch_active_work_orders(limit: int = 20):
    """Return active work orders for staff/dashboard style displays."""
    try:
        domain = [['state', 'not in', ['done', 'cancel', 'draft']]]
        fields = ['id', 'name', 'vehicle_plate', 'customer_id', 'state', 'date_planned', 'bff_uuid']
        orders = odoo_client.execute_kw(
            'drmoto.work.order',
            'search_read',
            [domain],
            {'fields': fields, 'limit': limit, 'order': 'date_planned desc'},
        )
        return orders
    except Exception as e:
        logger.error(f"Active list fetch error: {e}")
        return []


@router.get("/active/list")
async def list_active_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """List active work orders for authenticated staff users."""
    return _fetch_active_work_orders()


@router.get("/display/list")
async def list_display_work_orders():
    """Public, read-only work-order feed for the showroom/display screen."""
    return _fetch_active_work_orders()

@router.get("/customers/search")
async def search_customers(
    query: str = "",
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    """Search customers in Odoo (Live proxy). No auth required for login/search."""
    try:
        normalized_query = compact_whitespace(query) or ""
        # Search by name or phone
        domain = ['|', ['name', 'ilike', normalized_query], ['phone', 'ilike', normalized_query]] if normalized_query else []
        fields = ['id', 'name', 'phone', 'email', 'city']
        partners = odoo_client.execute_kw('res.partner', 'search_read', [domain], {'fields': fields, 'limit': limit})
        if normalized_query:
            partners = sorted(
                partners,
                key=lambda item: (
                    _customer_match_score(normalized_query, item),
                    int(item.get("id") or 0),
                ),
                reverse=True,
            )
        return partners
    except Exception as e:
        logger.error(f"Customer search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search customers")


def _render_document_html(doc_title: str, db_wo: WorkOrder, odoo_details: dict, process_record: dict | None = None) -> str:
    lines = odoo_details.get("lines", []) or []
    line_rows = []
    for line in lines:
        product = line.get("product_id")
        product_name = product[1] if isinstance(product, list) and len(product) > 1 else "-"
        line_rows.append(
            "<tr>"
            f"<td>{html.escape(product_name)}</td>"
            f"<td>{html.escape(str(line.get('name', '-')))}</td>"
            f"<td style='text-align:right'>{html.escape(str(line.get('quantity', 0)))}</td>"
            f"<td style='text-align:right'>{html.escape(str(line.get('price_unit', 0)))}</td>"
            f"<td style='text-align:right'>{html.escape(str(line.get('price_subtotal', 0)))}</td>"
            "</tr>"
        )

    if not line_rows:
        line_rows.append("<tr><td colspan='5' style='text-align:center'>暂无明细</td></tr>")

    customer = odoo_details.get("customer_id")
    customer_name = customer[1] if isinstance(customer, list) and len(customer) > 1 else db_wo.customer_id
    ref = odoo_details.get("name") or db_wo.uuid
    plate = odoo_details.get("vehicle_plate") or db_wo.vehicle_plate
    state = odoo_details.get("state") or db_wo.status
    planned = odoo_details.get("date_planned") or ""
    total = odoo_details.get("amount_total") or 0
    description = odoo_details.get("description") or db_wo.description or ""
    process_record = process_record or {}
    symptom_draft = process_record.get("symptom_draft") or ""
    symptom_confirmed = process_record.get("symptom_confirmed") or ""
    quick_check = process_record.get("quick_check") or {}
    odometer_km = quick_check.get("odometer_km")
    battery_voltage = quick_check.get("battery_voltage")
    tire_front_psi = quick_check.get("tire_front_psi")
    tire_rear_psi = quick_check.get("tire_rear_psi")
    engine_noise_note = quick_check.get("engine_noise_note") or ""

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(doc_title)} - {html.escape(str(ref))}</title>
  <style>
    body {{ font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; margin: 24px; color: #222; }}
    h1 {{ margin: 0 0 12px 0; font-size: 24px; }}
    .meta {{ margin-bottom: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }}
    .box {{ border: 1px solid #ddd; padding: 10px; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
    th {{ background: #f8f8f8; text-align: left; }}
    .foot {{ margin-top: 16px; display: flex; justify-content: space-between; }}
    .muted {{ color: #666; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>{html.escape(doc_title)}</h1>
  <div class="meta box">
    <div><strong>工单编号：</strong> {html.escape(str(ref))}</div>
    <div><strong>工单状态：</strong> {html.escape(str(state))}</div>
    <div><strong>客户名称：</strong> {html.escape(str(customer_name))}</div>
    <div><strong>车牌号码：</strong> {html.escape(str(plate))}</div>
    <div><strong>计划时间：</strong> {html.escape(str(planned))}</div>
    <div><strong>合计金额：</strong> {html.escape(str(total))}</div>
  </div>

  <div class="box">
    <strong>故障描述</strong>
    <div>{html.escape(str(description))}</div>
  </div>

  <div class="box" style="margin-top:12px;">
    <strong>过程记录</strong>
    <div style="margin-top:8px;"><strong>草稿症状登记：</strong> {html.escape(str(symptom_draft or '-'))}</div>
    <div style="margin-top:6px;"><strong>接车确认症状：</strong> {html.escape(str(symptom_confirmed or '-'))}</div>
    <div style="margin-top:6px;"><strong>快速检测：</strong>
      里程(km)={html.escape(str(odometer_km if odometer_km is not None else '-'))}，
      电瓶电压(V)={html.escape(str(battery_voltage if battery_voltage is not None else '-'))}，
      前胎压(psi)={html.escape(str(tire_front_psi if tire_front_psi is not None else '-'))}，
      后胎压(psi)={html.escape(str(tire_rear_psi if tire_rear_psi is not None else '-'))}，
      异响备注={html.escape(str(engine_noise_note or '-'))}
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>项目</th>
        <th>说明</th>
        <th>数量</th>
        <th>单价</th>
        <th>小计</th>
      </tr>
    </thead>
    <tbody>
      {''.join(line_rows)}
    </tbody>
  </table>

  <div class="foot">
    <div class="muted">由机车博士系统自动生成</div>
    <div>签字：___________</div>
  </div>
</body>
</html>
"""


def _doc_to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _doc_is_labor_item(name: str, product_name: str) -> bool:
    text = f"{name or ''} {product_name or ''}".lower()
    labor_keywords = [
        "工时", "人工", "维修", "检修", "调试", "拆装", "保养",
        "labor", "service", "repair", "inspection",
    ]
    return any(k in text for k in labor_keywords)


def _doc_render_line_rows(items: list[dict], empty_text: str) -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('project') or '-'))}</td>"
            f"<td>{html.escape(str(item.get('desc') or '-'))}</td>"
            f"<td style='text-align:right'>{html.escape(str(item.get('qty') or 0))}</td>"
            f"<td style='text-align:right'>{html.escape(str(item.get('unit_price') or 0))}</td>"
            f"<td style='text-align:right'>{html.escape(str(item.get('subtotal') or 0))}</td>"
            "</tr>"
        )
    if not rows:
        return f"<tr><td colspan='5' style='text-align:center'>{html.escape(empty_text)}</td></tr>"
    return "".join(rows)


def _build_doc_line_items(odoo_details: dict) -> dict:
    lines = odoo_details.get("lines", []) or []
    all_items = []
    for line in lines:
        product = line.get("product_id")
        product_name = product[1] if isinstance(product, list) and len(product) > 1 else "-"
        name = str(line.get("name", "-") or "-")
        qty = _doc_to_float(line.get("quantity"), 0.0)
        unit_price = _doc_to_float(line.get("price_unit"), 0.0)
        subtotal = _doc_to_float(line.get("price_subtotal"), 0.0)
        all_items.append(
            {
                "project": product_name,
                "desc": name,
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "is_labor": _doc_is_labor_item(name, product_name),
            }
        )
    labor_items = [x for x in all_items if x["is_labor"]]
    part_items = [x for x in all_items if not x["is_labor"]]
    part_total = sum(x["subtotal"] for x in part_items)
    labor_total = sum(x["subtotal"] for x in labor_items)
    grand_total = _doc_to_float(odoo_details.get("amount_total"), part_total + labor_total)
    return {
        "all_items": all_items,
        "labor_items": labor_items,
        "part_items": part_items,
        "part_total": part_total,
        "labor_total": labor_total,
        "grand_total": grand_total,
    }


def _build_doc_line_items_from_selected(selected_items: list[dict]) -> dict:
    all_items = []
    part_items = []
    labor_items = []
    for item in selected_items or []:
        service_name = str(item.get("service_name") or "-")
        repair_method = compact_whitespace(item.get("repair_method") or "") or "-"
        required_parts = item.get("required_parts") or []
        for part in required_parts:
            qty = _doc_to_float(part.get("qty"), 0.0)
            unit_price = _doc_to_float(part.get("unit_price"), 0.0)
            subtotal = round(qty * unit_price, 2)
            row = {
                "project": part.get("part_name") or part.get("part_no") or service_name,
                "desc": service_name,
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "is_labor": False,
            }
            all_items.append(row)
            part_items.append(row)
        labor_price = _doc_to_float(item.get("labor_price"), 0.0)
        labor_row = {
            "project": f"{service_name}工时",
            "desc": repair_method,
            "qty": 1.0,
            "unit_price": labor_price,
            "subtotal": labor_price,
            "is_labor": True,
        }
        all_items.append(labor_row)
        labor_items.append(labor_row)

    part_total = round(sum(x["subtotal"] for x in part_items), 2)
    labor_total = round(sum(x["subtotal"] for x in labor_items), 2)
    grand_total = round(sum(_doc_to_float(item.get("line_total"), 0.0) for item in selected_items or []), 2)
    if not grand_total:
        grand_total = round(part_total + labor_total, 2)
    return {
        "all_items": all_items,
        "labor_items": labor_items,
        "part_items": part_items,
        "part_total": part_total,
        "labor_total": labor_total,
        "grand_total": grand_total,
    }


def _render_customer_document_html(
    doc_type: str,
    doc_title: str,
    db_wo: WorkOrder,
    odoo_details: dict,
    process_record: dict | None = None,
    health_record: dict | None = None,
    selected_items: list[dict] | None = None,
    delivery_checklist: dict | None = None,
    store_settings: dict | None = None,
) -> str:
    return _render_customer_document_html_clean(
        doc_type,
        doc_title,
        db_wo,
        odoo_details,
        process_record,
        health_record,
        selected_items,
        delivery_checklist,
        store_settings,
    )


def _render_customer_document_html_clean(
    doc_type: str,
    doc_title: str,
    db_wo: WorkOrder,
    odoo_details: dict,
    process_record: dict | None = None,
    health_record: dict | None = None,
    selected_items: list[dict] | None = None,
    delivery_checklist: dict | None = None,
    store_settings: dict | None = None,
) -> str:
    selected_items = selected_items or []
    health_record = health_record or {}
    delivery_checklist = delivery_checklist or {}
    store_settings = store_settings or {}

    item_data = _build_doc_line_items_from_selected(selected_items) if selected_items else _build_doc_line_items(odoo_details)
    part_items = item_data["part_items"]
    labor_items = item_data["labor_items"]
    part_total = item_data["part_total"]
    labor_total = item_data["labor_total"]
    grand_total = item_data["grand_total"]

    customer = odoo_details.get("customer_id")
    customer_name = customer[1] if isinstance(customer, list) and len(customer) > 1 else db_wo.customer_id
    ref = odoo_details.get("name") or db_wo.uuid
    plate = odoo_details.get("vehicle_plate") or db_wo.vehicle_plate or "-"
    created_at = db_wo.created_at.strftime("%Y-%m-%d %H:%M") if db_wo.created_at else "-"
    description = compact_whitespace(odoo_details.get("description") or db_wo.description or "") or "-"
    vehicle_key = getattr(db_wo, "vehicle_key", None) or "-"
    store_name = store_settings.get("store_name") or "机车博士"
    header_note = store_settings.get("header_note") or "摩托车售后服务专业单据"
    customer_footer_note = store_settings.get("customer_footer_note") or "请客户核对维修项目、金额与交车说明后签字确认。"
    service_advice = store_settings.get("service_advice") or "建议客户按保养周期复检，并关注油液、制动与轮胎状态。"
    doc_label = "客户报价单" if doc_type == "quote" else "客户交付单"
    service_section_title = "报价项目明细" if doc_type == "quote" else "维修保养项目"
    notice_text = (
        "本报价单用于向客户确认本次维修保养范围与费用，实际施工以前台与客户最终确认内容为准。"
        if doc_type == "quote"
        else "本交付单用于留存本次施工与交车信息，建议客户妥善保存并按建议周期回店复查。"
    )
    if service_advice:
        notice_text = f"{notice_text} {service_advice}".strip()

    if selected_items:
        service_rows = []
        for item in selected_items:
            required_parts = item.get("required_parts") or []
            parts_text = "、".join(
                f"{part.get('part_name') or '-'} x{part.get('qty') or 0}"
                for part in required_parts
                if part.get("part_name")
            ) or "-"
            repair_method = compact_whitespace(item.get("repair_method") or "") or "-"
            service_rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('service_name') or '-'))}</td>"
                f"<td>{html.escape(repair_method)}</td>"
                f"<td>{html.escape(parts_text)}</td>"
                f"<td class='num'>{html.escape(str(item.get('parts_total') or 0))}</td>"
                f"<td class='num'>{html.escape(str(item.get('labor_price') or 0))}</td>"
                f"<td class='num strong'>{html.escape(str(item.get('line_total') or 0))}</td>"
                "</tr>"
            )
        service_rows_html = "".join(service_rows)
    else:
        service_rows_html = _doc_render_line_rows(item_data["all_items"], "暂无项目")

    part_rows = _doc_render_line_rows(part_items, "暂无配件费用")
    labor_rows = _doc_render_line_rows(labor_items, "暂无工时费用")

    delivery_section_html = ""
    if doc_type == "delivery-note":
        def _yes_no(value):
            return "已确认" if value else "未确认"

        delivery_rows_html = "".join(
            f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
            for label, value in [
                ("维修项目已向客户说明", _yes_no(delivery_checklist.get("explained_to_customer"))),
                ("旧件返还或处理方式已确认", _yes_no(delivery_checklist.get("returned_old_parts"))),
                ("下次保养建议已告知", _yes_no(delivery_checklist.get("next_service_notified"))),
                ("线下收款方式", _payment_method_label(delivery_checklist.get("payment_method"))),
                ("线下收款金额", str(delivery_checklist.get("payment_amount") if delivery_checklist.get("payment_amount") is not None else "-")),
                ("交车备注", compact_whitespace(delivery_checklist.get("notes") or "") or "-"),
            ]
        )
        delivery_section_html = f"""
    <section class="section">
      <div class="section-title">维修后车辆检查摘要</div>
      <div class="kv-grid">
        <div class="kv-item"><span>检查时间</span><strong>{html.escape(str(health_record.get("measured_at") or "-"))}</strong></div>
        <div class="kv-item"><span>里程 (km)</span><strong>{html.escape(str(health_record.get("odometer_km") if health_record.get("odometer_km") is not None else "-"))}</strong></div>
        <div class="kv-item"><span>电瓶电压 (V)</span><strong>{html.escape(str(health_record.get("battery_voltage") if health_record.get("battery_voltage") is not None else "-"))}</strong></div>
        <div class="kv-item"><span>前胎压 (psi)</span><strong>{html.escape(str(health_record.get("tire_front_psi") if health_record.get("tire_front_psi") is not None else "-"))}</strong></div>
        <div class="kv-item"><span>后胎压 (psi)</span><strong>{html.escape(str(health_record.get("tire_rear_psi") if health_record.get("tire_rear_psi") is not None else "-"))}</strong></div>
        <div class="kv-item wide"><span>检查备注</span><strong>{html.escape(str(health_record.get("notes") or "-"))}</strong></div>
      </div>
    </section>

    <section class="section">
      <div class="section-title">交车确认</div>
      <table>
        <tbody>{delivery_rows_html}</tbody>
      </table>
    </section>
"""

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(doc_title)} - {html.escape(str(ref))}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #ffffff; color: #1f2937; font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; }}
    .page {{ width: 210mm; min-height: 297mm; margin: 0 auto; padding: 14mm 14mm 16mm; background: #ffffff; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #2a8bc9; padding-bottom: 12px; }}
    .brand-title {{ font-size: 28px; font-weight: 800; color: #0f3d63; letter-spacing: 1px; }}
    .brand-subtitle {{ margin-top: 4px; font-size: 12px; color: #577187; }}
    .doc-side {{ text-align: right; }}
    .doc-type {{ font-size: 24px; font-weight: 800; color: #12344d; }}
    .doc-tag {{ display: inline-block; margin-top: 4px; padding: 4px 10px; font-size: 12px; font-weight: 700; color: #2a7fbc; background: #ecf6fc; border: 1px solid #c7dfef; }}
    .doc-meta {{ margin-top: 8px; font-size: 12px; line-height: 1.8; color: #5b7285; }}
    .intro {{ margin-top: 12px; padding: 10px 12px; border: 1px solid #d9e7f1; background: #f8fbfd; font-size: 12px; line-height: 1.8; color: #4e6477; }}
    .info-table {{ width: 100%; margin-top: 12px; border-collapse: collapse; table-layout: fixed; }}
    .info-table th, .info-table td {{ border: 1px solid #cfdde8; padding: 9px 10px; font-size: 12px; line-height: 1.6; vertical-align: top; }}
    .info-table th {{ width: 14%; background: #f3f8fb; color: #4e6477; font-weight: 700; text-align: left; }}
    .section {{ margin-top: 14px; }}
    .section-title {{ padding: 8px 10px; border-left: 4px solid #2a8bc9; background: #f4f9fc; color: #12344d; font-size: 15px; font-weight: 800; }}
    .section-note {{ margin-top: 8px; font-size: 12px; color: #60788b; line-height: 1.7; }}
    table {{ width: 100%; margin-top: 8px; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border: 1px solid #cfdde8; padding: 10px 10px; font-size: 12px; line-height: 1.7; vertical-align: top; }}
    th {{ background: #f7fafc; color: #486175; font-weight: 700; text-align: left; }}
    .num {{ text-align: right; white-space: nowrap; }}
    .strong {{ font-weight: 700; color: #12344d; }}
    .fee-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }}
    .total-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }}
    .total-box {{ border: 1px solid #bfd6e6; background: #f8fbfd; padding: 10px 12px; }}
    .total-box span {{ display: block; font-size: 11px; color: #6a8193; }}
    .total-box strong {{ display: block; margin-top: 6px; font-size: 18px; color: #10344f; }}
    .kv-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; }}
    .kv-item {{ border: 1px solid #d8e5ef; background: #fbfdfe; padding: 10px 12px; min-height: 72px; }}
    .kv-item.wide {{ grid-column: span 3; }}
    .kv-item span {{ display: block; font-size: 11px; color: #6b7f91; }}
    .kv-item strong {{ display: block; margin-top: 6px; font-size: 13px; line-height: 1.7; color: #12344d; }}
    .sign-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 10px; }}
    .sign-box {{ border: 1px solid #cfdde8; min-height: 92px; padding: 10px 12px; }}
    .sign-label {{ font-size: 12px; color: #667c8e; }}
    .sign-line {{ margin-top: 42px; border-top: 1px solid #9cb2c3; padding-top: 6px; font-size: 12px; color: #42586a; }}
    .footer {{ margin-top: 16px; display: flex; justify-content: space-between; font-size: 11px; color: #6c8293; line-height: 1.7; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <div class="brand-title">{html.escape(store_name)}</div>
        <div class="brand-subtitle">{html.escape(header_note)}</div>
      </div>
      <div class="doc-side">
        <div class="doc-type">{html.escape(doc_title)}</div>
        <div class="doc-tag">{html.escape(doc_label)}</div>
        <div class="doc-meta">
          <div>单据编号：{html.escape(str(ref))}</div>
          <div>生成时间：{html.escape(str(created_at))}</div>
        </div>
      </div>
    </div>

    <div class="intro">{html.escape(notice_text)}</div>

    <table class="info-table">
      <tr>
        <th>客户姓名</th><td>{html.escape(str(customer_name))}</td>
        <th>车牌号码</th><td>{html.escape(str(plate))}</td>
        <th>车型信息</th><td>{html.escape(str(vehicle_key))}</td>
      </tr>
      <tr>
        <th>业务说明</th><td colspan="5">{html.escape(str(description))}</td>
      </tr>
    </table>

    <section class="section">
      <div class="section-title">{html.escape(service_section_title)}</div>
      <div class="section-note">项目、所需配件与费用结构按本次工单已确认内容展示。</div>
      <table>
        <thead>
          <tr>
            <th style="width: 18%;">项目名称</th>
            <th style="width: 28%;">维修方法</th>
            <th style="width: 22%;">所需配件</th>
            <th class="num" style="width: 10%;">配件费</th>
            <th class="num" style="width: 10%;">工时费</th>
            <th class="num" style="width: 12%;">小计</th>
          </tr>
        </thead>
        <tbody>{service_rows_html}</tbody>
      </table>
    </section>

    <section class="section">
      <div class="section-title">费用汇总</div>
      <div class="fee-grid">
        <div>
          <div class="section-note">配件费用明细</div>
          <table>
            <thead><tr><th>项目</th><th>说明</th><th class="num">数量</th><th class="num">单价</th><th class="num">小计</th></tr></thead>
            <tbody>{part_rows}</tbody>
          </table>
        </div>
        <div>
          <div class="section-note">工时费用明细</div>
          <table>
            <thead><tr><th>项目</th><th>说明</th><th class="num">数量</th><th class="num">单价</th><th class="num">小计</th></tr></thead>
            <tbody>{labor_rows}</tbody>
          </table>
        </div>
      </div>
      <div class="total-row">
        <div class="total-box"><span>配件费用合计</span><strong>{html.escape(str(round(part_total, 2)))}</strong></div>
        <div class="total-box"><span>工时费用合计</span><strong>{html.escape(str(round(labor_total, 2)))}</strong></div>
        <div class="total-box"><span>总金额</span><strong>{html.escape(str(round(grand_total, 2)))}</strong></div>
      </div>
    </section>

    {delivery_section_html}

    <section class="section">
      <div class="section-title">签字确认</div>
      <div class="sign-grid">
        <div class="sign-box"><div class="sign-label">客户签字</div><div class="sign-line">签字 / 日期</div></div>
        <div class="sign-box"><div class="sign-label">服务顾问签字</div><div class="sign-line">签字 / 日期</div></div>
      </div>
    </section>

    <div class="footer">
      <div>{html.escape(store_name)} · 客户留存联</div>
      <div>{html.escape(customer_footer_note)}</div>
    </div>
  </div>
</body>
</html>
"""


def _render_document_html_v2(
    doc_type: str,
    doc_title: str,
    db_wo: WorkOrder,
    odoo_details: dict,
    process_record: dict | None = None,
    health_record: dict | None = None,
    selected_items: list[dict] | None = None,
    store_settings: dict | None = None,
) -> str:
    selected_items = selected_items or []
    store_settings = store_settings or {}
    item_data = _build_doc_line_items_from_selected(selected_items) if selected_items else _build_doc_line_items(odoo_details)
    all_items = item_data["all_items"]
    labor_items = item_data["labor_items"]
    part_items = item_data["part_items"]
    part_total = item_data["part_total"]
    labor_total = item_data["labor_total"]
    grand_total = item_data["grand_total"]

    customer = odoo_details.get("customer_id")
    customer_name = customer[1] if isinstance(customer, list) and len(customer) > 1 else db_wo.customer_id
    ref = odoo_details.get("name") or db_wo.uuid
    plate = odoo_details.get("vehicle_plate") or db_wo.vehicle_plate or "-"
    state = odoo_details.get("state") or db_wo.status or "-"
    planned = odoo_details.get("date_planned") or "-"
    created_at = db_wo.created_at.strftime("%Y-%m-%d %H:%M") if db_wo.created_at else "-"
    description = compact_whitespace(odoo_details.get("description") or db_wo.description or "") or "-"
    store_name = store_settings.get("store_name") or "机车博士"
    header_note = store_settings.get("header_note") or "门店内部维修与领料留档单据"
    internal_footer_note = store_settings.get("internal_footer_note") or "用于门店内部留档、责任追溯与施工复核。"

    process_record = process_record or {}
    symptom_draft = process_record.get("symptom_draft") or "-"
    symptom_confirmed = process_record.get("symptom_confirmed") or "-"
    quick_check = process_record.get("quick_check") or {}
    odometer_km = quick_check.get("odometer_km")
    battery_voltage = quick_check.get("battery_voltage")
    tire_front_psi = quick_check.get("tire_front_psi")
    tire_rear_psi = quick_check.get("tire_rear_psi")
    engine_noise_note = quick_check.get("engine_noise_note") or "-"

    health_record = health_record or {}
    health_measured_at = health_record.get("measured_at") or "-"
    health_odometer = health_record.get("odometer_km")
    health_battery = health_record.get("battery_voltage")
    health_front = health_record.get("tire_front_psi")
    health_rear = health_record.get("tire_rear_psi")
    health_rpm = health_record.get("engine_rpm")
    health_notes = health_record.get("notes") or "-"

    part_rows = _doc_render_line_rows(part_items, "暂无配件")
    labor_rows = _doc_render_line_rows(labor_items, "暂无工时")
    service_rows = _doc_render_line_rows(all_items, "暂无项目")
    total_quantity = round(
        sum(_doc_to_float(x["qty"], 0.0) for x in (part_items if doc_type == "pick-list" else all_items)),
        2,
    )
    service_count = len(part_items if doc_type == "pick-list" else all_items)

    doc_label = {
        "work-order": "内部维修工单",
        "pick-list": "内部领料单",
    }.get(doc_type, "内部单据")
    section_title = {
        "work-order": "维修项目明细",
        "pick-list": "领料明细",
    }.get(doc_type, "项目明细")
    sign_items = {
        "work-order": ["接车顾问", "施工技师", "质检确认"],
        "pick-list": ["仓库发料", "施工领料", "复核确认"],
    }.get(doc_type, ["经办人", "复核人", "负责人"])
    sign_html = "".join(
        f"<div class='sign-box'><div class='sign-label'>{html.escape(item)}</div><div class='sign-line'>签字 / 日期</div></div>"
        for item in sign_items
    )

    service_table_rows = part_rows if doc_type == "pick-list" else service_rows

    amount_section_html = f"""
    <section class="section">
      <div class="section-title">费用结构</div>
      <div class="fee-grid">
        <div>
          <div class="section-note">配件费用明细</div>
          <table><thead><tr><th>项目</th><th>说明</th><th class="num">数量</th><th class="num">单价</th><th class="num">小计</th></tr></thead><tbody>{part_rows}</tbody></table>
        </div>
        <div>
          <div class="section-note">工时费用明细</div>
          <table><thead><tr><th>项目</th><th>说明</th><th class="num">数量</th><th class="num">单价</th><th class="num">小计</th></tr></thead><tbody>{labor_rows}</tbody></table>
        </div>
      </div>
      <div class="total-row">
        <div class="total-box"><span>配件费用合计</span><strong>{html.escape(str(round(part_total, 2)))}</strong></div>
        <div class="total-box"><span>工时费用合计</span><strong>{html.escape(str(round(labor_total, 2)))}</strong></div>
        <div class="total-box"><span>总金额</span><strong>{html.escape(str(round(grand_total, 2)))}</strong></div>
      </div>
    </section>
""" if doc_type != "pick-list" else f"""
    <section class="section">
      <div class="section-title">领料汇总</div>
      <div class="total-row">
        <div class="total-box"><span>配件项目数</span><strong>{html.escape(str(len(part_items)))}</strong></div>
        <div class="total-box"><span>领料总数量</span><strong>{html.escape(str(round(sum(_doc_to_float(x['qty'], 0.0) for x in part_items), 2)))}</strong></div>
        <div class="total-box"><span>配件金额</span><strong>{html.escape(str(round(part_total, 2)))}</strong></div>
      </div>
    </section>
"""

    process_section_html = ""
    if doc_type == "work-order":
        process_section_html = f"""
    <section class="section">
      <div class="section-title">维修过程记录</div>
      <div class="kv-grid">
        <div class="kv-item"><span>草稿症状登记</span><strong>{html.escape(str(symptom_draft))}</strong></div>
        <div class="kv-item"><span>接车确认症状</span><strong>{html.escape(str(symptom_confirmed))}</strong></div>
        <div class="kv-item"><span>接车里程 (km)</span><strong>{html.escape(str(odometer_km if odometer_km is not None else '-'))}</strong></div>
        <div class="kv-item"><span>电瓶电压 (V)</span><strong>{html.escape(str(battery_voltage if battery_voltage is not None else '-'))}</strong></div>
        <div class="kv-item"><span>前胎压 (psi)</span><strong>{html.escape(str(tire_front_psi if tire_front_psi is not None else '-'))}</strong></div>
        <div class="kv-item"><span>后胎压 (psi)</span><strong>{html.escape(str(tire_rear_psi if tire_rear_psi is not None else '-'))}</strong></div>
        <div class="kv-item wide"><span>异响或补充备注</span><strong>{html.escape(str(engine_noise_note))}</strong></div>
      </div>
    </section>
"""
    elif doc_type == "pick-list":
        process_section_html = """
    <section class="section">
      <div class="section-title">流转说明</div>
      <div class="section-note">本领料单用于门店内部仓库发料、施工领料与复核留档，不对客户展示。</div>
    </section>
"""

    health_section_html = ""
    if doc_type == "work-order":
        health_section_html = f"""
    <section class="section">
      <div class="section-title">维修后车辆体检信息</div>
      <div class="kv-grid">
        <div class="kv-item"><span>体检时间</span><strong>{html.escape(str(health_measured_at))}</strong></div>
        <div class="kv-item"><span>体检里程 (km)</span><strong>{html.escape(str(health_odometer if health_odometer is not None else '-'))}</strong></div>
        <div class="kv-item"><span>发动机转速 (rpm)</span><strong>{html.escape(str(health_rpm if health_rpm is not None else '-'))}</strong></div>
        <div class="kv-item"><span>电瓶电压 (V)</span><strong>{html.escape(str(health_battery if health_battery is not None else '-'))}</strong></div>
        <div class="kv-item"><span>前胎压 (psi)</span><strong>{html.escape(str(health_front if health_front is not None else '-'))}</strong></div>
        <div class="kv-item"><span>后胎压 (psi)</span><strong>{html.escape(str(health_rear if health_rear is not None else '-'))}</strong></div>
        <div class="kv-item wide"><span>体检备注</span><strong>{html.escape(str(health_notes))}</strong></div>
      </div>
    </section>
"""

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(doc_title)} - {html.escape(str(ref))}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #ffffff; color: #1f2937; font-family: 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif; }}
    .page {{ width: 210mm; min-height: 297mm; margin: 0 auto; padding: 14mm 14mm 16mm; background: #ffffff; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #2a8bc9; padding-bottom: 12px; }}
    .brand-title {{ font-size: 28px; font-weight: 800; color: #0f3d63; letter-spacing: 1px; }}
    .brand-subtitle {{ margin-top: 4px; font-size: 12px; color: #577187; }}
    .doc-side {{ text-align: right; }}
    .doc-type {{ font-size: 24px; font-weight: 800; color: #12344d; }}
    .doc-tag {{ display: inline-block; margin-top: 4px; padding: 4px 10px; font-size: 12px; font-weight: 700; color: #2a7fbc; background: #ecf6fc; border: 1px solid #c7dfef; }}
    .doc-meta {{ margin-top: 8px; font-size: 12px; line-height: 1.8; color: #5b7285; }}
    .info-table {{ width: 100%; margin-top: 12px; border-collapse: collapse; table-layout: fixed; }}
    .info-table th, .info-table td {{ border: 1px solid #cfdde8; padding: 9px 10px; font-size: 12px; line-height: 1.6; vertical-align: top; }}
    .info-table th {{ width: 14%; background: #f3f8fb; color: #4e6477; font-weight: 700; text-align: left; }}
    .section {{ margin-top: 14px; }}
    .section-title {{ padding: 8px 10px; border-left: 4px solid #2a8bc9; background: #f4f9fc; color: #12344d; font-size: 15px; font-weight: 800; }}
    .section-note {{ margin-top: 8px; font-size: 12px; color: #60788b; line-height: 1.7; }}
    table {{ width: 100%; margin-top: 8px; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border: 1px solid #cfdde8; padding: 10px 10px; font-size: 12px; line-height: 1.7; vertical-align: top; }}
    th {{ background: #f7fafc; color: #486175; font-weight: 700; text-align: left; }}
    .num {{ text-align: right; white-space: nowrap; }}
    .fee-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }}
    .total-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }}
    .total-box {{ border: 1px solid #bfd6e6; background: #f8fbfd; padding: 10px 12px; }}
    .total-box span {{ display: block; font-size: 11px; color: #6a8193; }}
    .total-box strong {{ display: block; margin-top: 6px; font-size: 18px; color: #10344f; }}
    .kv-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; }}
    .kv-item {{ border: 1px solid #d8e5ef; background: #fbfdfe; padding: 10px 12px; min-height: 72px; }}
    .kv-item.wide {{ grid-column: span 3; }}
    .kv-item span {{ display: block; font-size: 11px; color: #6b7f91; }}
    .kv-item strong {{ display: block; margin-top: 6px; font-size: 13px; line-height: 1.7; color: #12344d; }}
    .sign-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 10px; }}
    .sign-box {{ border: 1px solid #cfdde8; min-height: 92px; padding: 10px 12px; }}
    .sign-label {{ font-size: 12px; color: #667c8e; }}
    .sign-line {{ margin-top: 42px; border-top: 1px solid #9cb2c3; padding-top: 6px; font-size: 12px; color: #42586a; }}
    .footer {{ margin-top: 16px; display: flex; justify-content: space-between; font-size: 11px; color: #6c8293; line-height: 1.7; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <div class="brand-title">{html.escape(store_name)}</div>
        <div class="brand-subtitle">{html.escape(header_note)}</div>
      </div>
      <div class="doc-side">
        <div class="doc-type">{html.escape(doc_title)}</div>
        <div class="doc-tag">{html.escape(doc_label)}</div>
        <div class="doc-meta">
          <div>工单编号：{html.escape(str(ref))}</div>
          <div>生成时间：{html.escape(str(created_at))}</div>
        </div>
      </div>
    </div>

    <table class="info-table">
      <tr>
        <th>客户姓名</th><td>{html.escape(str(customer_name))}</td>
        <th>车牌号码</th><td>{html.escape(str(plate))}</td>
        <th>工单状态</th><td>{html.escape(str(state))}</td>
      </tr>
      <tr>
        <th>计划时间</th><td>{html.escape(str(planned))}</td>
        <th>建单时间</th><td>{html.escape(str(created_at))}</td>
        <th>项目数 / 数量</th><td>{html.escape(str(service_count))} / {html.escape(str(total_quantity))}</td>
      </tr>
      <tr>
        <th>故障描述</th><td colspan="5">{html.escape(str(description))}</td>
      </tr>
    </table>

    <section class="section">
      <div class="section-title">{html.escape(section_title)}</div>
      <table>
        <thead><tr><th>项目</th><th>说明</th><th class="num">数量</th><th class="num">单价</th><th class="num">小计</th></tr></thead>
        <tbody>{service_table_rows}</tbody>
      </table>
    </section>

    {amount_section_html}
    {process_section_html}
    {health_section_html}

    <section class="section">
      <div class="section-title">签字确认</div>
      <div class="sign-grid">{sign_html}</div>
    </section>

    <div class="footer">
      <div>{html.escape(store_name)} · 内部留存联</div>
      <div>{html.escape(internal_footer_note)}</div>
    </div>
  </div>
</body>
</html>
"""


def _pdf_value(value) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _pdf_num(value) -> str:
    if value is None or value == "":
        return "-"
    try:
        num = float(value)
        return str(int(num)) if num.is_integer() else f"{num:.2f}"
    except Exception:
        return str(value)


def _ensure_pdf_font() -> str:
    font_name = "STSong-Light"
    try:
        pdfmetrics.getFont(font_name)
    except Exception:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def _pdf_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    safe_text = html.escape(_pdf_value(text)).replace("\n", "<br/>")
    return Paragraph(safe_text, style)


def _pdf_table(rows: list[list], col_widths: list[float], font_name: str, header=True) -> Table:
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 13),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfdde8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f9fc")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#12344d")),
            ("FONTNAME", (0, 0), (-1, 0), font_name),
        ])
    table.setStyle(TableStyle(style))
    return table


def _build_document_pdf(
    doc_type: str,
    doc_title: str,
    db_wo: WorkOrder,
    odoo_details: dict,
    process_record: dict | None = None,
    health_record: dict | None = None,
    selected_items: list[dict] | None = None,
    delivery_checklist: dict | None = None,
    store_settings: dict | None = None,
) -> bytes:
    font_name = _ensure_pdf_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName=font_name, fontSize=20, leading=24, textColor=colors.HexColor("#12344d"), spaceAfter=4)
    brand_style = ParagraphStyle("BrandTitle", parent=styles["Heading1"], fontName=font_name, fontSize=24, leading=28, textColor=colors.HexColor("#0f3d63"), spaceAfter=2)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#5b7285"))
    normal_style = ParagraphStyle("Body", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#1f2937"))
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=15, textColor=colors.HexColor("#12344d"), backColor=colors.HexColor("#f4f9fc"), borderPadding=6, leftIndent=0, spaceBefore=10, spaceAfter=6)

    process_record = process_record or {}
    health_record = health_record or {}
    selected_items = selected_items or []
    delivery_checklist = delivery_checklist or {}
    store_settings = store_settings or {}
    quick_check = process_record.get("quick_check") or {}
    odometer_km = quick_check.get("odometer_km")
    battery_voltage = quick_check.get("battery_voltage")
    tire_front_psi = quick_check.get("tire_front_psi")
    tire_rear_psi = quick_check.get("tire_rear_psi")
    engine_noise_note = process_record.get("engine_noise_note") or quick_check.get("engine_noise_note") or "-"
    item_data = _build_doc_line_items_from_selected(selected_items) if selected_items else _build_doc_line_items(odoo_details)
    part_items = item_data["part_items"]
    labor_items = item_data["labor_items"]
    all_items = item_data["all_items"]
    part_total = item_data["part_total"]
    labor_total = item_data["labor_total"]
    grand_total = item_data["grand_total"]

    customer = odoo_details.get("customer_id")
    customer_name = customer[1] if isinstance(customer, list) and len(customer) > 1 else db_wo.customer_id
    ref = odoo_details.get("name") or db_wo.uuid
    plate = odoo_details.get("vehicle_plate") or db_wo.vehicle_plate or "-"
    created_at = db_wo.created_at.strftime("%Y-%m-%d %H:%M") if db_wo.created_at else "-"
    description = compact_whitespace(odoo_details.get("description") or db_wo.description or "") or "-"
    vehicle_key = getattr(db_wo, "vehicle_key", None) or "-"
    state = odoo_details.get("state") or db_wo.status or "-"
    planned = odoo_details.get("date_planned") or "-"
    store_name = store_settings.get("store_name") or "机车博士"
    header_note = store_settings.get("header_note") or "摩托车售后服务专业单据"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    story = []

    header_table = Table([
        [
            [_pdf_paragraph(store_name, brand_style), _pdf_paragraph(header_note, meta_style)],
            [_pdf_paragraph(doc_title, title_style), _pdf_paragraph(f"单据编号：{ref}<br/>生成时间：{created_at}", meta_style)],
        ]
    ], colWidths=[100 * mm, 76 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor("#2a8bc9")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    info_rows = [
        [_pdf_paragraph("客户姓名", normal_style), _pdf_paragraph(customer_name, normal_style), _pdf_paragraph("车牌号码", normal_style), _pdf_paragraph(plate, normal_style), _pdf_paragraph("车型信息", normal_style), _pdf_paragraph(vehicle_key, normal_style)],
    ]
    if doc_type in {"work-order", "pick-list"}:
        info_rows.extend([
            [_pdf_paragraph("工单状态", normal_style), _pdf_paragraph(state, normal_style), _pdf_paragraph("计划时间", normal_style), _pdf_paragraph(planned, normal_style), _pdf_paragraph("建单时间", normal_style), _pdf_paragraph(created_at, normal_style)],
        ])
    info_rows.append([_pdf_paragraph("业务说明", normal_style), _pdf_paragraph(description, normal_style), "", "", "", ""])
    info_table = Table(info_rows, colWidths=[20 * mm, 40 * mm, 20 * mm, 40 * mm, 20 * mm, 36 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfdde8")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f8fb")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f3f8fb")),
        ("BACKGROUND", (4, 0), (4, -1), colors.HexColor("#f3f8fb")),
        ("SPAN", (1, len(info_rows) - 1), (-1, len(info_rows) - 1)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)

    story.append(Spacer(1, 8))
    story.append(_pdf_paragraph("项目明细", section_style))
    if doc_type in {"quote", "delivery-note"} and selected_items:
        project_rows = [[
            _pdf_paragraph("项目名称", normal_style),
            _pdf_paragraph("维修方法", normal_style),
            _pdf_paragraph("所需配件", normal_style),
            _pdf_paragraph("配件费", normal_style),
            _pdf_paragraph("工时费", normal_style),
            _pdf_paragraph("小计", normal_style),
        ]]
        for item in selected_items:
            required_parts = item.get("required_parts") or []
            parts_text = "、".join(
                f"{part.get('part_name') or '-'} x{part.get('qty') or 0}"
                for part in required_parts if part.get("part_name")
            ) or "-"
            project_rows.append([
                _pdf_paragraph(item.get("service_name") or "-", normal_style),
                _pdf_paragraph(compact_whitespace(item.get("repair_method") or "") or "-", normal_style),
                _pdf_paragraph(parts_text, normal_style),
                _pdf_paragraph(_pdf_num(item.get("parts_total")), normal_style),
                _pdf_paragraph(_pdf_num(item.get("labor_price")), normal_style),
                _pdf_paragraph(_pdf_num(item.get("line_total")), normal_style),
            ])
        story.append(_pdf_table(project_rows, [28 * mm, 52 * mm, 42 * mm, 18 * mm, 18 * mm, 18 * mm], font_name))
    else:
        service_rows = [[
            _pdf_paragraph("项目", normal_style),
            _pdf_paragraph("说明", normal_style),
            _pdf_paragraph("数量", normal_style),
            _pdf_paragraph("单价", normal_style),
            _pdf_paragraph("小计", normal_style),
        ]]
        for item in (part_items if doc_type == "pick-list" else all_items):
            service_rows.append([
                _pdf_paragraph(item.get("project") or "-", normal_style),
                _pdf_paragraph(item.get("desc") or "-", normal_style),
                _pdf_paragraph(_pdf_num(item.get("qty")), normal_style),
                _pdf_paragraph(_pdf_num(item.get("unit_price")), normal_style),
                _pdf_paragraph(_pdf_num(item.get("subtotal")), normal_style),
            ])
        story.append(_pdf_table(service_rows, [38 * mm, 74 * mm, 18 * mm, 22 * mm, 22 * mm], font_name))

    if doc_type != "pick-list":
        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("费用汇总", section_style))
        for title, items, total in [("配件费用明细", part_items, part_total), ("工时费用明细", labor_items, labor_total)]:
            story.append(_pdf_paragraph(title, meta_style))
            rows = [[_pdf_paragraph("项目", normal_style), _pdf_paragraph("说明", normal_style), _pdf_paragraph("数量", normal_style), _pdf_paragraph("单价", normal_style), _pdf_paragraph("小计", normal_style)]]
            if items:
                for item in items:
                    rows.append([
                        _pdf_paragraph(item.get("project") or "-", normal_style),
                        _pdf_paragraph(item.get("desc") or "-", normal_style),
                        _pdf_paragraph(_pdf_num(item.get("qty")), normal_style),
                        _pdf_paragraph(_pdf_num(item.get("unit_price")), normal_style),
                        _pdf_paragraph(_pdf_num(item.get("subtotal")), normal_style),
                    ])
            else:
                rows.append([_pdf_paragraph("-", normal_style), _pdf_paragraph("暂无", normal_style), _pdf_paragraph("-", normal_style), _pdf_paragraph("-", normal_style), _pdf_paragraph("-", normal_style)])
            story.append(_pdf_table(rows, [38 * mm, 74 * mm, 18 * mm, 22 * mm, 22 * mm], font_name))
            story.append(Spacer(1, 5))

        total_table = Table([[
            _pdf_paragraph(f"配件费用合计：{_pdf_num(part_total)}", normal_style),
            _pdf_paragraph(f"工时费用合计：{_pdf_num(labor_total)}", normal_style),
            _pdf_paragraph(f"总金额：{_pdf_num(grand_total)}", normal_style),
        ]], colWidths=[58 * mm, 58 * mm, 60 * mm])
        total_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fbfd")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#10344f")),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#bfd6e6")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(total_table)
    else:
        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("领料汇总", section_style))
        total_table = Table([[
            _pdf_paragraph(f"配件项目数：{len(part_items)}", normal_style),
            _pdf_paragraph(f"领料总数量：{_pdf_num(sum(_doc_to_float(x['qty'], 0.0) for x in part_items))}", normal_style),
            _pdf_paragraph(f"配件金额：{_pdf_num(part_total)}", normal_style),
        ]], colWidths=[58 * mm, 58 * mm, 60 * mm])
        total_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fbfd")),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#bfd6e6")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(total_table)

    if doc_type == "work-order":
        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("维修过程记录", section_style))
        process_rows = [
            [_pdf_paragraph("草稿症状登记", normal_style), _pdf_paragraph(process_record.get("symptom_draft") or "-", normal_style)],
            [_pdf_paragraph("接车确认症状", normal_style), _pdf_paragraph(process_record.get("symptom_confirmed") or "-", normal_style)],
            [_pdf_paragraph("接车里程 / 电压", normal_style), _pdf_paragraph(f"{_pdf_num(odometer_km)} km / {_pdf_num(battery_voltage)} V", normal_style)],
            [_pdf_paragraph("前后胎压", normal_style), _pdf_paragraph(f"{_pdf_num(tire_front_psi)} psi / {_pdf_num(tire_rear_psi)} psi", normal_style)],
            [_pdf_paragraph("异响或补充备注", normal_style), _pdf_paragraph(engine_noise_note, normal_style)],
        ]
        proc_table = Table(process_rows, colWidths=[36 * mm, 140 * mm])
        proc_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f8fb")),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfdde8")),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(proc_table)

        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("维修后车辆体检信息", section_style))
        health_rows = [
            [_pdf_paragraph("体检时间", normal_style), _pdf_paragraph(_pdf_value(health_record.get("measured_at")), normal_style)],
            [_pdf_paragraph("体检里程 / 转速", normal_style), _pdf_paragraph(f"{_pdf_num(health_record.get('odometer_km'))} km / {_pdf_num(health_record.get('engine_rpm'))} rpm", normal_style)],
            [_pdf_paragraph("电压 / 胎压", normal_style), _pdf_paragraph(f"{_pdf_num(health_record.get('battery_voltage'))} V / 前 {_pdf_num(health_record.get('tire_front_psi'))} 后 {_pdf_num(health_record.get('tire_rear_psi'))}", normal_style)],
            [_pdf_paragraph("体检备注", normal_style), _pdf_paragraph(health_record.get("notes") or "-", normal_style)],
        ]
        health_table = Table(health_rows, colWidths=[36 * mm, 140 * mm])
        health_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f8fb")),
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfdde8")),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(health_table)

    if doc_type == "delivery-note":
        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("维修后车辆检查摘要", section_style))
        health_rows = [
            [_pdf_paragraph("检查时间", normal_style), _pdf_paragraph(_pdf_value(health_record.get("measured_at")), normal_style)],
            [_pdf_paragraph("里程 / 电压", normal_style), _pdf_paragraph(f"{_pdf_num(health_record.get('odometer_km'))} km / {_pdf_num(health_record.get('battery_voltage'))} V", normal_style)],
            [_pdf_paragraph("前后胎压", normal_style), _pdf_paragraph(f"前 {_pdf_num(health_record.get('tire_front_psi'))} / 后 {_pdf_num(health_record.get('tire_rear_psi'))}", normal_style)],
            [_pdf_paragraph("检查备注", normal_style), _pdf_paragraph(health_record.get("notes") or "-", normal_style)],
        ]
        story.append(_pdf_table(health_rows, [36 * mm, 140 * mm], font_name, header=False))

        story.append(Spacer(1, 8))
        story.append(_pdf_paragraph("交车确认", section_style))
        delivery_rows = [
            [_pdf_paragraph("维修项目已向客户说明", normal_style), _pdf_paragraph("已确认" if delivery_checklist.get("explained_to_customer") else "未确认", normal_style)],
            [_pdf_paragraph("旧件返还或处理方式已确认", normal_style), _pdf_paragraph("已确认" if delivery_checklist.get("returned_old_parts") else "未确认", normal_style)],
            [_pdf_paragraph("下次保养建议已告知", normal_style), _pdf_paragraph("已确认" if delivery_checklist.get("next_service_notified") else "未确认", normal_style)],
            [_pdf_paragraph("线下收款方式 / 金额", normal_style), _pdf_paragraph(f"{_payment_method_label(delivery_checklist.get('payment_method'))} / {_pdf_num(delivery_checklist.get('payment_amount'))}", normal_style)],
            [_pdf_paragraph("交车备注", normal_style), _pdf_paragraph(delivery_checklist.get("notes") or "-", normal_style)],
        ]
        story.append(_pdf_table(delivery_rows, [52 * mm, 124 * mm], font_name, header=False))

    if doc_type in {"quote", "delivery-note"}:
        sign_rows = [[_pdf_paragraph("客户签字", normal_style), _pdf_paragraph("", normal_style), _pdf_paragraph("服务顾问签字", normal_style), _pdf_paragraph("", normal_style)]]
        sign_widths = [26 * mm, 62 * mm, 30 * mm, 58 * mm]
    else:
        labels = ["接车顾问", "施工技师", "质检确认"] if doc_type == "work-order" else ["仓库发料", "施工领料", "复核确认"]
        sign_rows = [[_pdf_paragraph(labels[0], normal_style), _pdf_paragraph("", normal_style), _pdf_paragraph(labels[1], normal_style), _pdf_paragraph("", normal_style), _pdf_paragraph(labels[2], normal_style), _pdf_paragraph("", normal_style)]]
        sign_widths = [18 * mm, 40 * mm, 18 * mm, 40 * mm, 18 * mm, 40 * mm]
    story.append(Spacer(1, 10))
    story.append(_pdf_paragraph("签字确认", section_style))
    sign_table = Table(sign_rows, colWidths=sign_widths, rowHeights=[18 * mm])
    sign_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfdde8")),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (1, 0), (1, 0), 0.8, colors.HexColor("#9cb2c3")),
    ]))
    if len(sign_widths) > 4:
        sign_table.setStyle(TableStyle([
            ("LINEBELOW", (3, 0), (3, 0), 0.8, colors.HexColor("#9cb2c3")),
            ("LINEBELOW", (5, 0), (5, 0), 0.8, colors.HexColor("#9cb2c3")),
        ]))
    else:
        sign_table.setStyle(TableStyle([
            ("LINEBELOW", (3, 0), (3, 0), 0.8, colors.HexColor("#9cb2c3")),
        ]))
    story.append(sign_table)

    doc.build(story)
    return buffer.getvalue()


@router.get("/{order_id}/documents/{doc_type}", response_class=HTMLResponse)
async def generate_work_order_document(
    order_id: str,
    doc_type: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    doc_titles = {
        "work-order": "维修工单",
        "quote": "报价单",
        "pick-list": "配件领料单",
        "delivery-note": "交付单",
    }

    if doc_type not in doc_titles:
        raise HTTPException(status_code=400, detail="Unsupported doc_type")

    store_id = resolve_store_id(request, current_user)
    db_wo, odoo_details = _load_order_snapshot(db, order_id, store_id)
    process_row = _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=db_wo.description)
    process_data = _process_record_to_response(db_wo.uuid, process_row)
    latest_health = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == db_wo.customer_id,
            VehicleHealthRecord.vehicle_plate == db_wo.vehicle_plate,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    health_data = None
    if latest_health:
        health_data = {
            "measured_at": latest_health.measured_at.isoformat() if latest_health.measured_at else None,
            "odometer_km": latest_health.odometer_km,
            "engine_rpm": latest_health.engine_rpm,
            "battery_voltage": latest_health.battery_voltage,
            "tire_front_psi": latest_health.tire_front_psi,
            "tire_rear_psi": latest_health.tire_rear_psi,
            "oil_life_percent": latest_health.oil_life_percent,
            "notes": latest_health.notes,
        }
    advanced_data = _advanced_profile_to_response(
        (
            db.query(WorkOrderAdvancedProfile)
            .filter(
                WorkOrderAdvancedProfile.store_id == store_id,
                WorkOrderAdvancedProfile.work_order_uuid == db_wo.uuid,
            )
            .first()
        )
    )
    store_settings = _resolve_document_branding(db, store_id)
    selected_items = _load_work_order_selected_items(db, store_id, order_id)
    delivery_checklist = _delivery_checklist_to_response(
        (
            db.query(WorkOrderDeliveryChecklist)
            .filter(
                WorkOrderDeliveryChecklist.store_id == store_id,
                WorkOrderDeliveryChecklist.work_order_uuid == db_wo.uuid,
            )
            .first()
        )
    )
    if doc_type in {"quote", "delivery-note"}:
        html_text = _render_customer_document_html_clean(
            doc_type,
            doc_titles[doc_type],
            db_wo,
            odoo_details,
            process_data,
            health_data,
            selected_items,
            delivery_checklist,
            store_settings,
        )
    else:
        html_text = _render_document_html_v2(
            doc_type,
            doc_titles[doc_type],
            db_wo,
            odoo_details,
            process_data,
            health_data,
            selected_items,
            store_settings,
        )
        html_text = _inject_document_sections(
            html_text,
            [
                _render_selected_services_section(doc_type, selected_items),
                _render_delivery_checklist_section(doc_type, delivery_checklist),
                _render_advanced_profile_section(doc_type, advanced_data),
            ],
    )
    return HTMLResponse(content=html_text)


@router.get("/{order_id}/documents/{doc_type}/pdf")
async def download_work_order_document_pdf(
    order_id: str,
    doc_type: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"]))
):
    doc_titles = {
        "work-order": "维修工单",
        "quote": "报价单",
        "pick-list": "配件领料单",
        "delivery-note": "交付单",
    }
    if doc_type not in doc_titles:
        raise HTTPException(status_code=400, detail="Unsupported doc_type")

    store_id = resolve_store_id(request, current_user)
    db_wo, odoo_details = _load_order_snapshot(db, order_id, store_id)
    process_row = _ensure_process_record(db, store_id, db_wo.uuid, draft_symptom=db_wo.description)
    process_data = _process_record_to_response(db_wo.uuid, process_row)
    latest_health = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == db_wo.customer_id,
            VehicleHealthRecord.vehicle_plate == db_wo.vehicle_plate,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    health_data = None
    if latest_health:
        health_data = {
            "measured_at": latest_health.measured_at.isoformat() if latest_health.measured_at else None,
            "odometer_km": latest_health.odometer_km,
            "engine_rpm": latest_health.engine_rpm,
            "battery_voltage": latest_health.battery_voltage,
            "tire_front_psi": latest_health.tire_front_psi,
            "tire_rear_psi": latest_health.tire_rear_psi,
            "oil_life_percent": latest_health.oil_life_percent,
            "notes": latest_health.notes,
        }
    selected_items = _load_work_order_selected_items(db, store_id, order_id)
    delivery_checklist = _delivery_checklist_to_response(
        (
            db.query(WorkOrderDeliveryChecklist)
            .filter(
                WorkOrderDeliveryChecklist.store_id == store_id,
                WorkOrderDeliveryChecklist.work_order_uuid == db_wo.uuid,
            )
            .first()
        ),
        db,
        store_id,
    )
    store_settings = _resolve_document_branding(db, store_id)
    pdf_bytes = _build_document_pdf(
        doc_type,
        doc_titles[doc_type],
        db_wo,
        odoo_details,
        process_data,
        health_data,
        selected_items,
        delivery_checklist,
        store_settings,
    )
    plate = compact_whitespace(db_wo.vehicle_plate or "未命名车辆") or "未命名车辆"
    file_name = f"{plate}-{doc_titles[doc_type]}-{db_wo.uuid[:8]}.pdf"
    encoded_name = quote(file_name)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
