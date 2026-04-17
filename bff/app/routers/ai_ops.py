import json
import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.audit import log_audit
from ..core.config import settings
from ..core.db import get_db
from ..core.store import resolve_store_id
from ..core.text import compact_whitespace, normalize_text
from ..integrations.odoo import odoo_client
from ..models import (
    PartCatalogItem,
    PartCatalogProfile,
    Quote,
    VehicleCatalogModel,
    VehicleHealthRecord,
    VehicleKnowledgeDocument,
    VehicleServiceTemplateItem,
    VehicleServiceTemplatePart,
    VehicleServiceTemplateProfile,
    WorkOrder,
    WorkOrderAdvancedProfile,
    WorkOrderProcessRecord,
)
from ..routers.catalog import _ensure_part_profile, _part_to_response
from ..routers.work_orders import (
    WORK_ORDER_TRANSITIONS,
    _advanced_profile_to_response,
    _create_partner_vehicle,
    _ensure_advanced_profile,
    _ensure_process_record,
    _find_catalog_model_id,
    _load_work_order_selected_items,
    _read_partner_vehicle_detail,
    _resolve_work_order_vehicle_key,
    _validate_transition_prerequisites,
)
from ..schemas.ai_ops import AiActionRequest, AiActionResponse, AiContextResponse
from ..schemas.auth import User
from ..schemas.catalog import PartCatalogItemCreate, PartCatalogItemUpdate
from ..schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerVehicleCreate,
    CustomerVehicleUpdate,
)
from ..schemas.quote import QuoteVersionCreate
from ..schemas.work_order import WorkOrderCreate

router = APIRouter(prefix="/ai/ops", tags=["AI Ops"])
logger = logging.getLogger("bff")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

ALLOWED_WRITE_ACTIONS = [
    "create_customer",
    "update_customer",
    "create_customer_vehicle",
    "update_customer_vehicle",
    "create_work_order",
    "append_work_order_internal_note",
    "update_work_order_status",
    "update_work_order_process_record",
    "create_quote_draft",
    "create_part",
    "update_part",
]


def _infer_query_domains(
    query: str | None,
    partner_id: int | None,
    plate: str | None,
    work_order_id: str | None,
    customers: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    work_orders: list[dict[str, Any]],
    vehicle_catalog_models: list[dict[str, Any]],
    parts: list[dict[str, Any]],
    knowledge_docs: list[dict[str, Any]],
) -> list[str]:
    text = normalize_text(query) or ""
    text = text.lower()
    domains: list[str] = []

    def add(name: str) -> None:
        if name and name not in domains:
            domains.append(name)

    if partner_id is not None or customers:
        add("customer")
    if plate or vehicles:
        add("vehicle")
    if work_order_id or work_orders:
        add("work_order")
    if vehicle_catalog_models:
        add("catalog")
    if parts:
        add("parts_inventory")
    if knowledge_docs:
        add("knowledge")

    keyword_map = {
        "customer": ["客户", "车主", "customer", "partner"],
        "vehicle": ["车辆", "车", "车牌", "vin", "plate", "vehicle"],
        "work_order": ["工单", "施工", "交付", "状态", "报价", "order", "quote"],
        "catalog": ["车型", "品牌", "目录", "catalog", "bmw", "奔驰", "宝马", "奥迪", "丰田", "本田", "x1", "x3", "x5", "3系", "5系", "7系"],
        "parts_inventory": ["配件", "库存", "part", "inventory", "产品", "材料"],
        "knowledge": ["怎么修", "维修", "步骤", "手册", "知识", "procedure", "manual", "spec", "保养", "更换", "机油", "滤芯", "火花塞", "刹车片"],
        "store_ops": ["待交付", "待施工", "ready", "quoted", "in progress", "看板", "总览", "门店"],
        "project_system": ["项目", "系统", "模块", "数据库", "架构", "前端", "后端", "odoo", "bff", "ai"],
    }
    for domain, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            add(domain)

    return domains or ["general"]


def _choose_primary_domain(domains: list[str], query: str | None = None) -> str:
    text = normalize_text(query) or ""
    text = text.lower()
    if "project_system" in domains and any(keyword in text for keyword in ["项目", "模块", "架构", "数据库", "前端", "后端", "odoo", "bff", "ai"]):
        return "project_system"
    if "knowledge" in domains and any(keyword in text for keyword in ["怎么修", "维修", "手册", "步骤", "保养", "更换", "机油", "滤芯", "火花塞", "刹车片"]):
        return "knowledge"
    if "catalog" in domains and any(keyword in text for keyword in ["车型", "品牌", "目录", "宝马", "奔驰", "奥迪", "bmw", "audi", "benz"]):
        return "catalog"
    priority = [
        "catalog",
        "work_order",
        "customer",
        "vehicle",
        "knowledge",
        "parts_inventory",
        "store_ops",
        "project_system",
        "general",
    ]
    for item in priority:
        if item in domains:
            return item
    return domains[0] if domains else "general"


def _source_hints_for_domains(domains: list[str]) -> list[str]:
    ordered: list[str] = []

    def add(value: str) -> None:
        if value not in ordered:
            ordered.append(value)

    for domain in domains:
        if domain == "customer":
            add("bff.customer")
            add("odoo.res.partner")
        elif domain == "vehicle":
            add("bff.vehicle")
            add("odoo.partner_vehicle")
        elif domain == "work_order":
            add("bff.work_order")
            add("odoo.work_order")
        elif domain == "catalog":
            add("bff.vehicle_catalog")
        elif domain == "parts_inventory":
            add("bff.parts")
            add("odoo.inventory")
        elif domain == "knowledge":
            add("bff.knowledge")
            add("ai.kb")
        elif domain == "store_ops":
            add("bff.dashboard")
        elif domain == "project_system":
            add("ai.project_brain")
            add("ai.project_ontology")
    return ordered


def _retrieval_plan_for_domains(domains: list[str]) -> list[str]:
    plan: list[str] = []

    def add(step: str) -> None:
        if step not in plan:
            plan.append(step)

    for domain in domains:
        if domain == "customer":
            add("先查客户主档，再查客户名下车辆和关联工单")
        elif domain == "vehicle":
            add("先查车辆档案，再查关联客户、工单和体检记录")
        elif domain == "work_order":
            add("先查工单详情，再查流程记录、报价和交付检查表")
        elif domain == "catalog":
            add("先查标准车型目录，再看规格、服务模板和文档")
        elif domain == "parts_inventory":
            add("先查配件目录；如果涉及实时库存，以 Odoo 库存为准")
        elif domain == "knowledge":
            add("先查知识文档和标准工序，再结合车型或当前车辆上下文")
        elif domain == "store_ops":
            add("先查门店总览和运营看板，再下钻到对应工单列表")
        elif domain == "project_system":
            add("优先基于项目认知档案、数据源地图和 ontology 回答")
    return plan


def _decode_user_from_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    username = normalize_text(payload.get("sub"))
    role = normalize_text(payload.get("role")) or "staff"
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return User(
        username=username,
        email=normalize_text(payload.get("email")),
        role=role,
        disabled=False,
    )


async def _authorize_ai_ops(
    request: Request,
    token: str | None = Depends(oauth2_optional),
) -> User:
    internal_secret = request.headers.get("X-Internal-Secret")
    if settings.WEBHOOK_SHARED_SECRET and internal_secret == settings.WEBHOOK_SHARED_SECRET:
        return User(username="ai-service", role="service", disabled=False)

    if token:
        user = _decode_user_from_token(token)
        if (user.role or "").lower() not in {"admin", "manager", "staff", "keeper", "cashier", "service"}:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    if settings.ENABLE_DEV_ENDPOINTS and request.headers.get("X-Internal-Source") == "ai-service":
        return User(username="ai-service-dev", role="service", disabled=False)

    raise HTTPException(status_code=401, detail="AI ops authorization required")


def _safe_odoo_execute(model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
    try:
        return odoo_client.execute_kw(model, method, args, kwargs or {})
    except Exception as exc:
        logger.warning("AI ops Odoo call failed for %s.%s: %s", model, method, exc)
        return [] if method.endswith("read") or method.startswith("search") else None


def _load_partner_detail(partner_id: int) -> dict[str, Any] | None:
    rows = _safe_odoo_execute(
        "res.partner",
        "search_read",
        [[["id", "=", partner_id]]],
        {"fields": ["id", "name", "phone", "email"], "limit": 1},
    )
    if not rows:
        return None
    row = rows[0]
    return {
        "id": int(row["id"]),
        "name": normalize_text(row.get("name")) or "",
        "phone": normalize_text(row.get("phone")),
        "email": normalize_text(row.get("email")),
    }


def _search_partners(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = compact_whitespace(query)
    if not q:
        return []
    rows = _safe_odoo_execute(
        "res.partner",
        "search_read",
        [["|", ["name", "ilike", q], ["phone", "ilike", q]]],
        {"fields": ["id", "name", "phone", "email"], "limit": limit},
    )
    return [
        {
            "id": int(row["id"]),
            "name": normalize_text(row.get("name")) or "",
            "phone": normalize_text(row.get("phone")),
            "email": normalize_text(row.get("email")),
        }
        for row in rows
    ]


def _search_partner_vehicle_ids(partner_id: int | None, plate: str | None) -> list[int]:
    domain = []
    if partner_id is not None:
        domain.append(["partner_id", "=", partner_id])
    if plate:
        domain.append(["license_plate", "=", plate])
    if not domain:
        return []
    rows = _safe_odoo_execute(
        "drmoto.partner.vehicle",
        "search_read",
        [domain],
        {"fields": ["id"], "limit": 20},
    )
    if not rows and plate:
        fuzzy_domain = []
        if partner_id is not None:
            fuzzy_domain.append(["partner_id", "=", partner_id])
        fuzzy_domain.append(["license_plate", "ilike", plate])
        rows = _safe_odoo_execute(
            "drmoto.partner.vehicle",
            "search_read",
            [fuzzy_domain],
            {"fields": ["id"], "limit": 20},
        )
    return [int(row["id"]) for row in rows if row.get("id")]


def _load_partner_vehicles(db: Session, partner_id: int | None = None, plate: str | None = None) -> list[dict[str, Any]]:
    vehicle_ids = _search_partner_vehicle_ids(partner_id, plate)
    vehicles: list[dict[str, Any]] = []
    for partner_vehicle_id in vehicle_ids:
        try:
            vehicles.append(_read_partner_vehicle_detail(db, partner_vehicle_id, fallback_partner_id=partner_id))
        except Exception as exc:
            logger.warning("AI ops failed to load partner vehicle %s: %s", partner_vehicle_id, exc)
    return vehicles


def _quote_summary_for_work_order(db: Session, store_id: str, work_order_uuid: str) -> dict[str, Any]:
    rows = (
        db.query(Quote)
        .filter(Quote.store_id == store_id, Quote.work_order_uuid == work_order_uuid)
        .order_by(Quote.version.desc())
        .all()
    )
    latest = rows[0] if rows else None
    active = next((row for row in rows if row.is_active), None)
    return {
        "active_version": active.version if active else None,
        "active_status": active.status if active else None,
        "latest_version": latest.version if latest else None,
        "latest_status": latest.status if latest else None,
        "latest_amount_total": float(latest.amount_total) if latest else None,
        "version_count": len(rows),
    }


def _load_work_order_context(db: Session, store_id: str, work_order: WorkOrder) -> dict[str, Any]:
    process_row = _ensure_process_record(db, store_id, work_order.uuid, draft_symptom=work_order.description)
    quick_check = process_row.quick_check_json if isinstance(process_row.quick_check_json, dict) else {}
    health_row = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == store_id,
            VehicleHealthRecord.customer_id == work_order.customer_id,
            VehicleHealthRecord.vehicle_plate == work_order.vehicle_plate,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    advanced_profile = (
        db.query(WorkOrderAdvancedProfile)
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrderAdvancedProfile.work_order_uuid == work_order.uuid,
        )
        .first()
    )
    return {
        "id": work_order.uuid,
        "status": work_order.status,
        "customer_id": work_order.customer_id,
        "vehicle_plate": work_order.vehicle_plate,
        "description": work_order.description,
        "odoo_id": work_order.odoo_id,
        "quote_summary": _quote_summary_for_work_order(db, store_id, work_order.uuid),
        "selected_services": _load_work_order_selected_items(db, store_id, work_order.uuid),
        "process_record": {
            "symptom_draft": process_row.symptom_draft,
            "symptom_confirmed": process_row.symptom_confirmed,
            "quick_check": quick_check,
        },
        "latest_health_record": (
            {
                "measured_at": health_row.measured_at.isoformat() if health_row and health_row.measured_at else None,
                "odometer_km": float(health_row.odometer_km) if health_row else None,
                "battery_voltage": health_row.battery_voltage if health_row else None,
                "oil_life_percent": health_row.oil_life_percent if health_row else None,
                "notes": health_row.notes if health_row else None,
            }
            if health_row
            else None
        ),
        "advanced_profile": _advanced_profile_to_response(advanced_profile),
    }


def _search_work_orders(
    db: Session,
    store_id: str,
    work_order_id: str | None = None,
    customer_id: int | None = None,
    plate: str | None = None,
    query: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    q = db.query(WorkOrder).filter(WorkOrder.store_id == store_id)
    if work_order_id:
        q = q.filter(WorkOrder.uuid == work_order_id)
    if customer_id is not None:
        q = q.filter(WorkOrder.customer_id == str(customer_id))
    if plate:
        q = q.filter(
            or_(
                WorkOrder.vehicle_plate == plate,
                WorkOrder.vehicle_plate.ilike(f"%{plate}"),
            )
        )
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            or_(
                WorkOrder.vehicle_plate.ilike(pattern),
                WorkOrder.description.ilike(pattern),
                WorkOrder.uuid.ilike(pattern),
            )
        )
    rows = q.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc()).limit(limit).all()
    return [_load_work_order_context(db, store_id, row) for row in rows]


def _recommend_services(db: Session, model_id: int | None, limit: int = 8) -> list[dict[str, Any]]:
    if not model_id:
        return []
    rows = (
        db.query(VehicleServiceTemplateItem)
        .filter(
            VehicleServiceTemplateItem.model_id == model_id,
            VehicleServiceTemplateItem.is_active.is_(True),
        )
        .order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc())
        .limit(limit)
        .all()
    )
    ids = [row.id for row in rows]
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile)
        .filter(VehicleServiceTemplateProfile.template_item_id.in_(ids or [-1]))
        .all()
    }
    parts_map: dict[int, list[dict[str, Any]]] = {}
    part_rows = (
        db.query(VehicleServiceTemplatePart)
        .filter(VehicleServiceTemplatePart.template_item_id.in_(ids or [-1]))
        .order_by(VehicleServiceTemplatePart.sort_order.asc(), VehicleServiceTemplatePart.id.asc())
        .all()
    )
    for row in part_rows:
        parts_map.setdefault(row.template_item_id, []).append(
            {
                "part_no": row.part_no,
                "part_name": row.part_name,
                "qty": float(row.qty),
                "unit_price": row.unit_price,
                "is_optional": bool(row.is_optional),
            }
        )
    result = []
    for row in rows:
        profile = profile_map.get(row.id)
        result.append(
            {
                "template_item_id": row.id,
                "service_code": row.part_code,
                "service_name": row.part_name,
                "repair_method": row.repair_method,
                "labor_hours": row.labor_hours,
                "labor_price": profile.labor_price if profile else None,
                "suggested_price": profile.suggested_price if profile else None,
                "required_parts": parts_map.get(row.id, []),
            }
        )
    return result


def _knowledge_docs(db: Session, model_id: int | None, limit: int = 8) -> list[dict[str, Any]]:
    if not model_id:
        return []
    rows = (
        db.query(VehicleKnowledgeDocument)
        .filter(VehicleKnowledgeDocument.model_id == model_id)
        .order_by(VehicleKnowledgeDocument.created_at.desc(), VehicleKnowledgeDocument.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "title": row.title,
            "file_name": row.file_name,
            "file_url": row.file_url,
            "category": row.category,
            "review_status": row.review_status,
        }
        for row in rows
    ]


def _search_parts(db: Session, query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = compact_whitespace(query)
    if not q:
        return []
    rows = (
        db.query(PartCatalogItem)
        .filter(
            PartCatalogItem.is_active.is_(True),
            or_(
                PartCatalogItem.part_no.ilike(f"%{q}%"),
                PartCatalogItem.name.ilike(f"%{q}%"),
                PartCatalogItem.brand.ilike(f"%{q}%"),
            ),
        )
        .order_by(PartCatalogItem.id.desc())
        .limit(limit)
        .all()
    )
    profile_map = {
        row.part_id: row
        for row in db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id.in_([item.id for item in rows] or [-1])).all()
    }
    return [_part_to_response(row, profile_map.get(row.id)) for row in rows]


def _search_vehicle_catalog_models(db: Session, query: str, limit: int = 12) -> list[dict[str, Any]]:
    q = compact_whitespace(query)
    if not q:
        return []
    for filler in [
        "查询",
        "查一下",
        "看一下",
        "帮我查",
        "车辆库",
        "车型库",
        "车型",
        "车系",
        "有什么",
        "哪些",
        "有哪些",
        "里",
        "中",
        "的",
    ]:
        q = q.replace(filler, " ")
    q = compact_whitespace(q)
    if not q:
        q = compact_whitespace(query)
    normalized_query = normalize_text(q).lower()
    brand_alias_map = {
        "bmw": ["bmw", "宝马"],
        "宝马": ["bmw", "宝马"],
        "benz": ["benz", "mercedes", "奔驰"],
        "mercedes": ["benz", "mercedes", "奔驰"],
        "奔驰": ["benz", "mercedes", "奔驰"],
        "audi": ["audi", "奥迪"],
        "奥迪": ["audi", "奥迪"],
        "toyota": ["toyota", "丰田"],
        "丰田": ["toyota", "丰田"],
        "honda": ["honda", "本田"],
        "本田": ["honda", "本田"],
    }
    brand_hints: list[str] = []
    for alias, values in brand_alias_map.items():
        if alias in normalized_query:
            brand_hints.extend(values)
    brand_hints = list(dict.fromkeys(brand_hints))
    specific_model_hints = []
    for pattern in [r"\bx\s?[1-9]\b", r"[3578]系", r"[a-z]{1,3}\s?\d{2,3}"]:
        specific_model_hints.extend(match.strip() for match in re.findall(pattern, normalized_query, flags=re.IGNORECASE))
    specific_model_hints = [hint.replace(" ", "") for hint in specific_model_hints if hint.strip()]
    tokens = [
        token for token in normalized_query.replace("/", " ").replace("-", " ").split()
        if token and token not in {"查询", "查一下", "看一下", "帮我查", "车辆库", "车型库", "车型", "车系"}
    ]
    pattern = f"%{q}%"
    rows = (
        db.query(VehicleCatalogModel)
        .filter(
            VehicleCatalogModel.is_active.is_(True),
            or_(
                VehicleCatalogModel.brand.ilike(pattern),
                VehicleCatalogModel.model_name.ilike(pattern),
                VehicleCatalogModel.category.ilike(pattern),
            ),
        )
        .order_by(
            VehicleCatalogModel.brand.asc(),
            VehicleCatalogModel.model_name.asc(),
            VehicleCatalogModel.year_from.desc(),
        )
        .limit(limit)
        .all()
    )
    if rows and tokens:
        filtered_rows = []
        for row in rows:
            brand_text = compact_whitespace(str(row.brand or "")).lower()
            haystack = " ".join(
                [
                    brand_text,
                    compact_whitespace(str(row.model_name or "")).lower(),
                    compact_whitespace(str(row.category or "")).lower(),
                ]
            )
            normalized_haystack = haystack.replace(" ", "")
            if brand_hints and not any(hint in brand_text for hint in brand_hints):
                continue
            if specific_model_hints and not any(hint in normalized_haystack for hint in specific_model_hints):
                continue
            if all(token in haystack for token in tokens):
                filtered_rows.append(row)
        if filtered_rows:
            rows = filtered_rows[:limit]
    if not rows:
        fallback_rows = (
            db.query(VehicleCatalogModel)
            .filter(VehicleCatalogModel.is_active.is_(True))
            .order_by(
                VehicleCatalogModel.brand.asc(),
                VehicleCatalogModel.model_name.asc(),
                VehicleCatalogModel.year_from.desc(),
            )
            .all()
        )
        lowered = normalized_query
        rows = [
            row
            for row in fallback_rows
            if (
                (
                    not brand_hints
                    or any(hint in compact_whitespace(str(row.brand or "")).lower() for hint in brand_hints)
                )
                and (
                    lowered in compact_whitespace(str(row.brand or "")).lower()
                    or lowered in compact_whitespace(str(row.model_name or "")).lower()
                    or lowered in compact_whitespace(str(row.category or "")).lower()
                    or compact_whitespace(str(row.brand or "")).lower() in lowered
                    or compact_whitespace(str(row.model_name or "")).lower() in lowered
                or (
                    tokens
                    and all(
                        token in " ".join(
                            [
                                compact_whitespace(str(row.brand or "")).lower(),
                                compact_whitespace(str(row.model_name or "")).lower(),
                                compact_whitespace(str(row.category or "")).lower(),
                            ]
                        )
                        for token in tokens
                    )
                )
                    or (
                        specific_model_hints
                        and any(
                            hint in (
                                compact_whitespace(str(row.model_name or "")).lower().replace(" ", "")
                                + " "
                                + compact_whitespace(str(row.category or "")).lower().replace(" ", "")
                            )
                            for hint in specific_model_hints
                        )
                    )
                )
            )
        ][:limit]
    return [
        {
            "id": row.id,
            "brand": row.brand,
            "model_name": row.model_name,
            "year_from": row.year_from,
            "year_to": row.year_to,
            "displacement_cc": row.displacement_cc,
            "category": row.category,
        }
        for row in rows
    ]


def _resolve_primary_customer(
    customers: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    work_orders: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if customers:
        return customers[0]
    if vehicles and vehicles[0].get("partner_id"):
        return {"id": vehicles[0]["partner_id"]}
    if work_orders and work_orders[0].get("customer_id"):
        try:
            return {"id": int(work_orders[0]["customer_id"])}
        except Exception:
            return None
    return None


def _resolve_primary_vehicle(vehicles: list[dict[str, Any]], work_orders: list[dict[str, Any]]) -> dict[str, Any] | None:
    if vehicles:
        return vehicles[0]
    if work_orders:
        return {"license_plate": work_orders[0].get("vehicle_plate")}
    return None


@router.get("/context", response_model=AiContextResponse)
async def get_ai_context(
    request: Request,
    query: str | None = Query(None),
    partner_id: int | None = Query(None),
    plate: str | None = Query(None),
    work_order_id: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: User = Depends(_authorize_ai_ops),
):
    store_id = resolve_store_id(request, actor)
    normalized_query = compact_whitespace(query)
    normalized_plate = compact_whitespace(plate)

    customers = []
    if partner_id is not None:
        row = _load_partner_detail(partner_id)
        customers = [row] if row else []
    elif normalized_query:
        customers = _search_partners(normalized_query)

    vehicles = _load_partner_vehicles(db, partner_id=partner_id, plate=normalized_plate)
    if not vehicles and customers:
        vehicles = _load_partner_vehicles(db, partner_id=customers[0]["id"])
    vehicle_catalog_models = _search_vehicle_catalog_models(db, normalized_query or "")

    customer_ref = customers[0]["id"] if customers else partner_id
    work_orders = _search_work_orders(
        db,
        store_id,
        work_order_id=work_order_id,
        customer_id=customer_ref,
        plate=normalized_plate,
        query=normalized_query if work_order_id is None and normalized_plate is None else None,
    )
    if not vehicles and work_orders:
        first_order = work_orders[0] or {}
        fallback_customer_id = None
        try:
            if first_order.get("customer_id") is not None:
                fallback_customer_id = int(first_order.get("customer_id"))
        except Exception:
            fallback_customer_id = None
        fallback_plate = compact_whitespace(first_order.get("vehicle_plate"))
        vehicles = _load_partner_vehicles(db, partner_id=fallback_customer_id, plate=fallback_plate)
    primary_customer = _resolve_primary_customer(customers, vehicles, work_orders)
    if primary_customer and "name" not in primary_customer:
        detailed = _load_partner_detail(int(primary_customer["id"]))
        if detailed:
            customers = [detailed] + customers
            primary_customer = detailed

    primary_vehicle = _resolve_primary_vehicle(vehicles, work_orders)
    catalog_model_id = None
    if primary_vehicle and primary_vehicle.get("catalog_model_id"):
        catalog_model_id = primary_vehicle["catalog_model_id"]
    elif primary_vehicle and primary_vehicle.get("make") and primary_vehicle.get("model") and primary_vehicle.get("year"):
        catalog_model_id = _find_catalog_model_id(
            db,
            primary_vehicle.get("make"),
            primary_vehicle.get("model"),
            primary_vehicle.get("year"),
            primary_vehicle.get("engine_code"),
        )
        primary_vehicle["catalog_model_id"] = catalog_model_id

    parts = _search_parts(db, normalized_query or "")
    recommended_services = _recommend_services(db, catalog_model_id)
    knowledge_docs = _knowledge_docs(db, catalog_model_id)
    query_domains = _infer_query_domains(
        normalized_query,
        partner_id,
        normalized_plate,
        work_order_id,
        customers,
        vehicles,
        work_orders,
        vehicle_catalog_models,
        parts,
        knowledge_docs,
    )
    if (
        "project_system" in query_domains
        and any(domain in query_domains for domain in ["catalog", "customer", "vehicle", "work_order", "knowledge", "parts_inventory"])
        and not any(keyword in (normalized_query or "") for keyword in ["模块", "架构", "数据库", "前端", "后端", "odoo", "bff", "ai"])
    ):
        query_domains = [domain for domain in query_domains if domain != "project_system"]
    primary_domain = _choose_primary_domain(query_domains, normalized_query)

    return {
        "store_id": store_id,
        "query": normalized_query,
        "query_domains": query_domains,
        "primary_domain": primary_domain,
        "source_hints": _source_hints_for_domains(query_domains),
        "retrieval_plan": _retrieval_plan_for_domains(query_domains),
        "matched_customer": primary_customer,
        "matched_vehicle": primary_vehicle,
        "matched_work_order": work_orders[0] if work_orders else None,
        "customers": customers[:10],
        "vehicles": vehicles[:10],
        "vehicle_catalog_models": vehicle_catalog_models[:12],
        "work_orders": work_orders[:10],
        "recommended_services": recommended_services,
        "knowledge_docs": knowledge_docs,
        "parts": parts,
        "write_capabilities": ALLOWED_WRITE_ACTIONS,
    }


def _create_work_order_record(
    db: Session,
    store_id: str,
    payload: WorkOrderCreate,
) -> dict[str, Any]:
    try:
        customer_id = int(payload.customer_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="customer_id must be a positive integer") from exc
    if customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id must be a positive integer")
    odoo_payload = {
        "name": "New",
        "customer_id": customer_id,
        "vehicle_plate": payload.vehicle_plate,
        "description": payload.description,
        "bff_uuid": "pending",
    }
    odoo_id = odoo_client.execute_kw("drmoto.work.order", "create", [odoo_payload])
    if not odoo_id:
        raise HTTPException(status_code=500, detail="Failed to create work order in Odoo")
    name_rows = odoo_client.execute_kw("drmoto.work.order", "read", [[odoo_id], ["name"]])
    odoo_ref = name_rows[0]["name"] if name_rows else None

    row = WorkOrder(
        uuid=str(uuid.uuid4()),
        store_id=store_id,
        odoo_id=odoo_id,
        customer_id=str(customer_id),
        vehicle_plate=payload.vehicle_plate,
        vehicle_key=_resolve_work_order_vehicle_key(db, customer_id, payload.vehicle_plate),
        description=payload.description,
        status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _ensure_process_record(db, store_id, row.uuid, draft_symptom=payload.description)
    try:
        odoo_client.execute_kw("drmoto.work.order", "write", [[odoo_id], {"bff_uuid": row.uuid}])
    except Exception as exc:
        logger.warning("AI ops failed to backfill BFF UUID for work order %s: %s", row.uuid, exc)
    return {
        "id": row.uuid,
        "status": row.status,
        "data": {"vehicle_plate": row.vehicle_plate, "odoo_ref": odoo_ref},
    }


def _append_internal_note(
    db: Session,
    store_id: str,
    work_order_id: str,
    note: str,
    actor: User,
) -> dict[str, Any]:
    work_order = (
        db.query(WorkOrder)
        .filter(WorkOrder.store_id == store_id, WorkOrder.uuid == work_order_id)
        .first()
    )
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    normalized_note = compact_whitespace(note)
    if not normalized_note:
        raise HTTPException(status_code=400, detail="note is required")
    profile = _ensure_advanced_profile(db, store_id, work_order_id)
    existing = compact_whitespace(profile.internal_notes or "")
    profile.internal_notes = f"{existing}\n{normalized_note}".strip() if existing else normalized_note
    profile.updated_by = actor.username
    db.commit()
    db.refresh(profile)
    return _advanced_profile_to_response(profile)


def _create_quote_draft(
    db: Session,
    store_id: str,
    work_order_id: str,
    payload: QuoteVersionCreate,
    actor: User,
) -> dict[str, Any]:
    work_order = (
        db.query(WorkOrder)
        .filter(WorkOrder.store_id == store_id, WorkOrder.uuid == work_order_id)
        .first()
    )
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Quote items cannot be empty")

    latest = (
        db.query(Quote)
        .filter(Quote.store_id == store_id, Quote.work_order_uuid == work_order_id)
        .order_by(Quote.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1
    items_json = [item.model_dump() for item in payload.items]
    amount_total = round(sum(float(item.qty) * float(item.unit_price) for item in payload.items), 2)
    quote = Quote(
        store_id=store_id,
        work_order_uuid=work_order_id,
        version=version,
        items_json=items_json,
        amount_total=amount_total,
        is_active=False,
        status="draft",
        created_by=actor.username,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return {
        "work_order_id": work_order_id,
        "version": quote.version,
        "status": quote.status,
        "is_active": quote.is_active,
        "amount_total": float(quote.amount_total),
        "items": quote.items_json or [],
    }


def _update_work_order_process_record(
    db: Session,
    store_id: str,
    work_order_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    work_order = (
        db.query(WorkOrder)
        .filter(WorkOrder.store_id == store_id, WorkOrder.uuid == work_order_id)
        .first()
    )
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    row = _ensure_process_record(db, store_id, work_order.uuid, draft_symptom=work_order.description)
    patch = {key: value for key, value in payload.items() if key in {"symptom_draft", "symptom_confirmed", "quick_check"}}
    if not patch:
        raise HTTPException(status_code=400, detail="No process fields to update")
    if "symptom_draft" in patch:
        row.symptom_draft = compact_whitespace(patch.get("symptom_draft"))
        if row.symptom_draft:
            work_order.description = row.symptom_draft
    if "symptom_confirmed" in patch:
        row.symptom_confirmed = compact_whitespace(patch.get("symptom_confirmed"))
    if "quick_check" in patch and isinstance(patch.get("quick_check"), dict):
        current_quick = row.quick_check_json if isinstance(row.quick_check_json, dict) else {}
        row.quick_check_json = {**current_quick, **patch.get("quick_check")}
    db.commit()
    db.refresh(row)
    return {
        "work_order_id": work_order.uuid,
        "symptom_draft": row.symptom_draft,
        "symptom_confirmed": row.symptom_confirmed,
        "quick_check": row.quick_check_json if isinstance(row.quick_check_json, dict) else {},
    }


def _update_work_order_status(
    db: Session,
    store_id: str,
    work_order_id: str,
    status: str,
    actor: User,
) -> dict[str, Any]:
    work_order = (
        db.query(WorkOrder)
        .filter(WorkOrder.store_id == store_id, WorkOrder.uuid == work_order_id)
        .first()
    )
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    target_status = compact_whitespace(status or "")
    if not target_status:
        raise HTTPException(status_code=400, detail="status is required")
    target_status = target_status.lower()
    allowed_next = WORK_ORDER_TRANSITIONS.get(work_order.status or "draft", set())
    if target_status not in allowed_next:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid status transition: {work_order.status} -> {target_status}. Allowed: {sorted(allowed_next)}",
        )
    _validate_transition_prerequisites(db, store_id, work_order, target_status)
    before_state = {"status": work_order.status}
    if work_order.odoo_id:
        try:
            odoo_client.execute_kw("drmoto.work.order", "write", [[work_order.odoo_id], {"state": target_status}])
        except Exception as exc:
            logger.warning("AI ops failed to sync work order status to Odoo: %s", exc)
    work_order.status = target_status
    db.commit()
    db.refresh(work_order)
    log_audit(
        db,
        actor_id=actor.username,
        action="ai_ops:update_work_order_status",
        target=f"work_order:{work_order.uuid}",
        before=before_state,
        after={"status": target_status},
        store_id=store_id,
    )
    return {"work_order_id": work_order.uuid, "status": work_order.status}


@router.post("/actions", response_model=AiActionResponse)
async def execute_ai_action(
    payload: AiActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(_authorize_ai_ops),
):
    store_id = resolve_store_id(request, actor)
    action = compact_whitespace(payload.action or "")
    if action not in ALLOWED_WRITE_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")

    result: dict[str, Any]
    risk_level = "low"

    if action == "create_customer":
        customer = CustomerCreate(**payload.payload)
        new_id = odoo_client.execute_kw(
            "res.partner",
            "create",
            [{"name": customer.name, "phone": customer.phone, "email": customer.email}],
        )
        vehicles = [_create_partner_vehicle(db, new_id, vehicle) for vehicle in customer.vehicles]
        result = {
            "id": int(new_id),
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "vehicles": vehicles,
        }
    elif action == "update_customer":
        partner_id = int(payload.payload.get("partner_id") or 0)
        if partner_id <= 0:
            raise HTTPException(status_code=400, detail="partner_id is required")
        patch = CustomerUpdate(**payload.payload)
        vals = patch.model_dump(exclude_unset=True)
        if not vals:
            raise HTTPException(status_code=400, detail="No fields to update")
        odoo_client.execute_kw("res.partner", "write", [[partner_id], vals])
        updated = _load_partner_detail(partner_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Customer not found after update")
        result = updated
        risk_level = "medium"
    elif action == "create_customer_vehicle":
        partner_id = int(payload.payload.get("partner_id") or 0)
        if partner_id <= 0:
            raise HTTPException(status_code=400, detail="partner_id is required")
        vehicle_payload = dict(payload.payload)
        vehicle_payload.pop("partner_id", None)
        result = _create_partner_vehicle(db, partner_id, CustomerVehicleCreate(**vehicle_payload))
    elif action == "update_customer_vehicle":
        partner_id = int(payload.payload.get("partner_id") or 0)
        partner_vehicle_id = int(payload.payload.get("partner_vehicle_id") or 0)
        if partner_id <= 0 or partner_vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="partner_id and partner_vehicle_id are required")
        patch = CustomerVehicleUpdate(**payload.payload)
        rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["id", "=", partner_vehicle_id], ["partner_id", "=", partner_id]]],
            {"fields": ["id"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Vehicle record not found")
        vals = patch.model_dump(exclude_unset=True)
        if not vals:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "catalog_model_id" in vals or "make" in vals or "model" in vals or "year" in vals or "engine_code" in vals:
            current = _read_partner_vehicle_detail(db, partner_vehicle_id, fallback_partner_id=partner_id)
            merged = {**current, **{k: v for k, v in vals.items() if v is not None}}
            resolved = CustomerVehicleCreate(
                catalog_model_id=merged.get("catalog_model_id"),
                license_plate=merged["license_plate"],
                make=merged["make"],
                model=merged["model"],
                year=merged["year"],
                engine_code=merged.get("engine_code"),
                vin=merged.get("vin"),
                color=merged.get("color"),
            )
            from ..routers.work_orders import _ensure_vehicle_model, _resolve_vehicle_input

            vals["vehicle_id"] = _ensure_vehicle_model(_resolve_vehicle_input(db, resolved))
            vals.pop("catalog_model_id", None)
            vals.pop("make", None)
            vals.pop("model", None)
            vals.pop("year", None)
            vals.pop("engine_code", None)
        odoo_client.execute_kw("drmoto.partner.vehicle", "write", [[partner_vehicle_id], vals])
        result = _read_partner_vehicle_detail(db, partner_vehicle_id, fallback_partner_id=partner_id)
        risk_level = "medium"
    elif action == "create_work_order":
        work_order = WorkOrderCreate(**payload.payload)
        result = _create_work_order_record(db, store_id, work_order)
        risk_level = "medium"
    elif action == "append_work_order_internal_note":
        work_order_id = compact_whitespace(payload.payload.get("work_order_id"))
        result = _append_internal_note(db, store_id, work_order_id or "", str(payload.payload.get("note") or ""), actor)
    elif action == "update_work_order_status":
        work_order_id = compact_whitespace(payload.payload.get("work_order_id"))
        result = _update_work_order_status(db, store_id, work_order_id or "", str(payload.payload.get("status") or ""), actor)
        risk_level = "medium"
    elif action == "update_work_order_process_record":
        work_order_id = compact_whitespace(payload.payload.get("work_order_id"))
        process_payload = dict(payload.payload)
        process_payload.pop("work_order_id", None)
        result = _update_work_order_process_record(db, store_id, work_order_id or "", process_payload)
        risk_level = "medium"
    elif action == "create_quote_draft":
        work_order_id = compact_whitespace(payload.payload.get("work_order_id"))
        if not work_order_id:
            raise HTTPException(status_code=400, detail="work_order_id is required")
        quote_payload = dict(payload.payload)
        quote_payload.pop("work_order_id", None)
        result = _create_quote_draft(db, store_id, work_order_id, QuoteVersionCreate(**quote_payload), actor)
        risk_level = "medium"
    elif action == "create_part":
        part = PartCatalogItemCreate(**payload.payload)
        existing = db.query(PartCatalogItem.id).filter(PartCatalogItem.part_no == part.part_no).first()
        if existing:
            raise HTTPException(status_code=400, detail="part_no already exists")
        row = PartCatalogItem(
            part_no=part.part_no,
            name=part.name,
            brand=part.brand,
            category=part.category,
            unit=part.unit,
            compatible_model_ids=part.compatible_model_ids,
            min_stock=part.min_stock,
            is_active=part.is_active,
        )
        db.add(row)
        db.flush()
        profile = _ensure_part_profile(db, row.id)
        profile.sale_price = part.sale_price
        profile.cost_price = part.cost_price
        profile.stock_qty = part.stock_qty
        profile.supplier_name = part.supplier_name
        db.commit()
        db.refresh(row)
        db.refresh(profile)
        result = _part_to_response(row, profile)
        risk_level = "medium"
    else:
        part_id = int(payload.payload.get("part_id") or 0)
        if part_id <= 0:
            raise HTTPException(status_code=400, detail="part_id is required")
        patch = PartCatalogItemUpdate(**payload.payload)
        row = db.query(PartCatalogItem).filter(PartCatalogItem.id == part_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Part not found")
        updates = patch.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "part_no" in updates:
            conflict = (
                db.query(PartCatalogItem.id)
                .filter(PartCatalogItem.part_no == updates["part_no"], PartCatalogItem.id != part_id)
                .first()
            )
            if conflict:
                raise HTTPException(status_code=400, detail="part_no already exists")
        profile = _ensure_part_profile(db, row.id)
        for key in ("sale_price", "cost_price", "stock_qty", "supplier_name"):
            if key in updates:
                setattr(profile, key, updates.pop(key))
        for key, value in updates.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        db.refresh(profile)
        result = _part_to_response(row, profile)
        risk_level = "medium"

    log_audit(
        db,
        actor_id=actor.username,
        action=f"ai_ops:{action}",
        target=json.dumps({"store_id": store_id}, ensure_ascii=True),
        before=None,
        after=result,
        store_id=store_id,
    )
    return {"status": "ok", "action": action, "result": result, "risk_level": risk_level}
