
import re
from datetime import datetime
from difflib import SequenceMatcher

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import require_roles
from ..data.moto_catalog_seed import DEFAULT_PART_ITEMS, DEFAULT_VEHICLE_MODELS
from ..models import (
    PartCatalogItem,
    PartCatalogProfile,
    Procedure,
    ProcedureStep,
    AppSetting,
    VehicleCatalogModel,
    VehicleCatalogSpec,
    VehicleKnowledgeSegment,
    VehicleServicePackage,
    VehicleServicePackageItem,
    VehicleServiceTemplateItem,
    VehicleServiceTemplatePart,
    VehicleServiceTemplateProfile,
)
from ..schemas.auth import User
from ..schemas.catalog import (
    BatchDeleteRequest,
    PartCatalogItemCreate,
    PartCatalogItemResponse,
    PartCatalogItemUpdate,
    VehicleCatalogModelCreate,
    VehicleCatalogModelResponse,
    VehicleCatalogModelUpdate,
    VehicleServiceTemplateItemCreate,
    VehicleServiceTemplateItemResponse,
    VehicleServicePackageCreate,
    VehicleServicePackageItemCreate,
    VehicleServicePackageItemResponse,
    VehicleServicePackageResponse,
    VehicleServicePackageUpdate,
    VehicleServiceTemplatePartCreate,
    VehicleServiceTemplatePartResponse,
    VehicleServiceTemplateItemUpdate,
)

router = APIRouter(prefix="/mp/catalog", tags=["Catalog"])
_SEARCH_TOKEN_RE = re.compile(r"[\s\-_/]+")


class VehicleCatalogSpecPayload(BaseModel):
    spec_key: str
    spec_label: str
    spec_type: str | None = None
    spec_value: str | None = None
    spec_unit: str | None = None
    source_page: str | None = None
    source_text: str | None = None
    review_status: str | None = "confirmed"


def _normalize_search_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    return compact_spaces(text)


def compact_spaces(value: str) -> str:
    return " ".join(str(value or "").split())


def _split_search_tokens(value: str | None) -> list[str]:
    normalized = _normalize_search_text(value)
    return [token for token in _SEARCH_TOKEN_RE.split(normalized) if token]


def _text_match_score(query: str, target: str | None) -> float:
    query_norm = _normalize_search_text(query)
    target_norm = _normalize_search_text(target)
    if not query_norm or not target_norm:
        return 0.0
    if query_norm == target_norm:
        return 120.0
    score = 0.0
    if target_norm.startswith(query_norm):
        score += 80.0
    elif query_norm in target_norm:
        score += 55.0

    target_tokens = _split_search_tokens(target_norm)
    query_tokens = _split_search_tokens(query_norm)
    for token in query_tokens:
        if token in target_tokens:
            score += 18.0
        elif any(item.startswith(token) for item in target_tokens):
            score += 12.0
        elif token in target_norm:
            score += 8.0

    ratio = SequenceMatcher(None, query_norm, target_norm).ratio()
    score += ratio * 20.0
    return score


def _rank_vehicle_model(row: VehicleCatalogModel, query: str) -> tuple[float, int, str, str]:
    score = 0.0
    query_norm = _normalize_search_text(query)
    model_norm = _normalize_search_text(row.model_name)
    brand_norm = _normalize_search_text(row.brand)
    combo_norm = _normalize_search_text(f"{row.brand} {row.model_name}")
    if query_norm and model_norm == query_norm:
        score += 260.0
    elif query_norm and combo_norm == query_norm:
        score += 220.0
    elif query_norm and brand_norm == query_norm:
        score += 180.0
    score += _text_match_score(query, row.model_name) * 1.4
    score += _text_match_score(query, row.brand) * 1.15
    score += _text_match_score(query, row.category)
    score += _text_match_score(query, row.default_engine_code) * 0.85
    score += _text_match_score(query, f"{row.brand} {row.model_name}") * 1.2
    if str(row.year_from or "") in str(query):
        score += 10.0
    if str(row.displacement_cc or "") in str(query):
        score += 8.0
    return (
        score,
        int(row.year_from or 0),
        _normalize_search_text(row.brand),
        _normalize_search_text(row.model_name),
    )


def _rank_part(row: PartCatalogItem, query: str) -> tuple[float, str, str]:
    score = 0.0
    score += _text_match_score(query, row.part_no) * 1.5
    score += _text_match_score(query, row.name) * 1.25
    score += _text_match_score(query, row.brand)
    score += _text_match_score(query, row.category) * 0.8
    return (
        score,
        _normalize_search_text(row.part_no),
        _normalize_search_text(row.name),
    )
    source: str | None = "manual"
    notes: str | None = None


class VehicleCatalogSpecResponse(VehicleCatalogSpecPayload):
    id: int
    model_id: int

MOTO58_BASE = "https://m.58moto.com/clientApi"
MOTO58_PLATFORM = 11
MOTO58_VERSION = "3.62.40"
MOTO58_DEVICE_ID = "E69D1D04-7904-4934-B4B2-C662B8093AA1"
_YEAR_RE = re.compile(r"(19\d{2}|20\d{2})")
_DISPLACEMENT_RE = re.compile(r"(\d{2,4})\s*cc", re.IGNORECASE)
BASELINE_PART_SPECS = [
    {"part_no": "GEN-OIL-10W40", "name": "机油 10W-40", "category": "油液", "unit": "瓶", "sale_price": 120, "cost_price": 85},
    {"part_no": "GEN-OIL-FILTER", "name": "机油滤芯", "category": "滤芯", "unit": "个", "sale_price": 45, "cost_price": 25},
    {"part_no": "GEN-BRAKE-FLUID-DOT4", "name": "刹车油 DOT4", "category": "油液", "unit": "瓶", "sale_price": 68, "cost_price": 35},
    {"part_no": "GEN-AIR-FILTER", "name": "空气滤芯", "category": "滤芯", "unit": "个", "sale_price": 78, "cost_price": 42},
    {"part_no": "GEN-SPARK-PLUG", "name": "火花塞", "category": "点火", "unit": "支", "sale_price": 78, "cost_price": 38},
    {"part_no": "GEN-CHAIN-LUBE", "name": "链条清洁润滑剂", "category": "养护", "unit": "瓶", "sale_price": 68, "cost_price": 35},
    {"part_no": "GEN-COOLANT", "name": "冷却液", "category": "油液", "unit": "瓶", "sale_price": 88, "cost_price": 46},
    {"part_no": "GEN-FRONT-BRAKE-PADS", "name": "前刹车片", "category": "制动", "unit": "套", "sale_price": 118, "cost_price": 65},
    {"part_no": "GEN-REAR-BRAKE-PADS", "name": "后刹车片", "category": "制动", "unit": "套", "sale_price": 108, "cost_price": 58},
]
BASELINE_SERVICE_SPECS = [
    {
        "service_code": "PM-OIL",
        "service_name": "更换机油",
        "labor_hours": 0.5,
        "labor_price": 60,
        "suggested_price": 180,
        "repair_method": "放净旧机油，检查放油螺丝和垫片，按标准加入新机油并复查液位。",
        "required_parts": [{"part_no": "GEN-OIL-10W40", "part_name": "机油 10W-40", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-OIL-FILTER",
        "service_name": "更换机油+机滤",
        "labor_hours": 0.8,
        "labor_price": 80,
        "suggested_price": 245,
        "repair_method": "更换机油并同步更换机油滤芯，检查密封面并启动车辆确认无渗漏。",
        "required_parts": [
            {"part_no": "GEN-OIL-10W40", "part_name": "机油 10W-40", "qty": 1, "sort_order": 10},
            {"part_no": "GEN-OIL-FILTER", "part_name": "机油滤芯", "qty": 1, "sort_order": 20},
        ],
    },
    {
        "service_code": "PM-BRAKE-FLUID",
        "service_name": "更换刹车油",
        "labor_hours": 0.8,
        "labor_price": 80,
        "suggested_price": 148,
        "repair_method": "抽排旧刹车油并按前后制动回路排空气，确认手感、行程和渗漏情况。",
        "required_parts": [{"part_no": "GEN-BRAKE-FLUID-DOT4", "part_name": "刹车油 DOT4", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-AIR-FILTER",
        "service_name": "更换空气滤芯",
        "labor_hours": 0.3,
        "labor_price": 40,
        "suggested_price": 118,
        "repair_method": "拆检空气滤芯盒，清洁安装位并更换空气滤芯，复位外壳并确认进气状态。",
        "required_parts": [{"part_no": "GEN-AIR-FILTER", "part_name": "空气滤芯", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-SPARK-PLUG",
        "service_name": "更换火花塞",
        "labor_hours": 0.4,
        "labor_price": 50,
        "suggested_price": 128,
        "repair_method": "拆装火花塞并检查燃烧情况，按规范力矩安装新火花塞，确认点火顺畅。",
        "required_parts": [{"part_no": "GEN-SPARK-PLUG", "part_name": "火花塞", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-CHAIN-SERVICE",
        "service_name": "链条清洁保养",
        "labor_hours": 0.5,
        "labor_price": 60,
        "suggested_price": 128,
        "repair_method": "清洁链条并检查松紧度、磨损和链轮状态，完成润滑和张紧调整。",
        "required_parts": [{"part_no": "GEN-CHAIN-LUBE", "part_name": "链条清洁润滑剂", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-COOLANT",
        "service_name": "更换冷却液",
        "labor_hours": 0.8,
        "labor_price": 80,
        "suggested_price": 168,
        "repair_method": "放净旧冷却液，冲洗冷却系统并加注新冷却液，排气后确认液位和温度表现。",
        "required_parts": [{"part_no": "GEN-COOLANT", "part_name": "冷却液", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-FRONT-BRAKE-PADS",
        "service_name": "更换前刹车片",
        "labor_hours": 0.6,
        "labor_price": 70,
        "suggested_price": 188,
        "repair_method": "拆检前制动卡钳及导向结构，更换前刹车片并确认磨合、回位和手感。",
        "required_parts": [{"part_no": "GEN-FRONT-BRAKE-PADS", "part_name": "前刹车片", "qty": 1, "sort_order": 10}],
    },
    {
        "service_code": "PM-REAR-BRAKE-PADS",
        "service_name": "更换后刹车片",
        "labor_hours": 0.6,
        "labor_price": 70,
        "suggested_price": 178,
        "repair_method": "拆检后制动总成，更换后刹车片并确认回位、磨合和制动力输出。",
        "required_parts": [{"part_no": "GEN-REAR-BRAKE-PADS", "part_name": "后刹车片", "qty": 1, "sort_order": 10}],
    },
]
BASELINE_SERVICE_PACKAGE_SPECS = [
    {
        "package_code": "PKG-BASIC",
        "package_name": "基础保养套餐",
        "description": "适合常规到店保养，覆盖机油、机滤与链条基础养护。",
        "recommended_interval_km": 3000,
        "recommended_interval_months": 6,
        "service_codes": ["PM-OIL-FILTER", "PM-CHAIN-SERVICE"],
        "sort_order": 10,
    },
    {
        "package_code": "PKG-PERIODIC",
        "package_name": "周期保养套餐",
        "description": "适合中期保养，加入空气滤芯与火花塞检查/更换。",
        "recommended_interval_km": 6000,
        "recommended_interval_months": 12,
        "service_codes": ["PM-OIL-FILTER", "PM-AIR-FILTER", "PM-SPARK-PLUG", "PM-CHAIN-SERVICE"],
        "sort_order": 20,
    },
    {
        "package_code": "PKG-SAFETY",
        "package_name": "制动安全套餐",
        "description": "适合制动状态重点检查与恢复，涵盖刹车油和前后制动耗材。",
        "recommended_interval_km": 12000,
        "recommended_interval_months": 18,
        "service_codes": ["PM-BRAKE-FLUID", "PM-FRONT-BRAKE-PADS", "PM-REAR-BRAKE-PADS"],
        "sort_order": 30,
    },
]


def _normalize_year_to(year_from: int, year_to: int | None) -> int:
    if year_to is None:
        return year_from
    if year_to < year_from:
        raise HTTPException(status_code=400, detail="year_to must be >= year_from")
    return year_to


def _to_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def _extract_years(*texts) -> list[int]:
    years: list[int] = []
    for text in texts:
        if not text:
            continue
        for matched in _YEAR_RE.findall(str(text)):
            year = int(matched)
            if 1950 <= year <= 2100:
                years.append(year)
    return years


def _extract_displacement_cc(*texts) -> int | None:
    for text in texts:
        if not text:
            continue
        match = _DISPLACEMENT_RE.search(str(text))
        if match:
            return int(match.group(1))
    return None


def _fetch_moto58_json(path: str, params: dict | None = None, timeout_seconds: int = 20):
    query = {
        "platform": MOTO58_PLATFORM,
        "version": MOTO58_VERSION,
        "deviceId": MOTO58_DEVICE_ID,
    }
    if params:
        query.update(params)
    resp = requests.get(f"{MOTO58_BASE}{path}", params=query, timeout=timeout_seconds)
    resp.raise_for_status()
    payload = resp.json()
    code = payload.get("code")
    if code not in (0, 200):
        raise ValueError(f"58moto api error code={code}, msg={payload.get('msg')}")
    return payload


def _ensure_part_profile(db: Session, part_id: int) -> PartCatalogProfile:
    profile = db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id == part_id).first()
    if profile:
        return profile
    profile = PartCatalogProfile(part_id=part_id)
    db.add(profile)
    db.flush()
    return profile


def _ensure_service_profile(db: Session, template_item_id: int) -> VehicleServiceTemplateProfile:
    profile = (
        db.query(VehicleServiceTemplateProfile)
        .filter(VehicleServiceTemplateProfile.template_item_id == template_item_id)
        .first()
    )
    if profile:
        return profile
    profile = VehicleServiceTemplateProfile(template_item_id=template_item_id)
    db.add(profile)
    db.flush()
    return profile


def _part_to_response(row: PartCatalogItem, profile: PartCatalogProfile | None = None) -> dict:
    return PartCatalogItemResponse(
        id=row.id,
        part_no=row.part_no,
        name=row.name,
        brand=row.brand,
        category=row.category,
        unit=row.unit,
        compatible_model_ids=row.compatible_model_ids or [],
        min_stock=row.min_stock,
        sale_price=profile.sale_price if profile else None,
        cost_price=profile.cost_price if profile else None,
        stock_qty=profile.stock_qty if profile else None,
        supplier_name=profile.supplier_name if profile else None,
        is_active=row.is_active,
    ).model_dump()


def _serialize_service_required_parts(db: Session, template_item_ids: list[int]) -> dict[int, list[dict]]:
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
        row.part_id: row
        for row in db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id.in_(part_ids)).all()
    } if part_ids else {}

    result: dict[int, list[dict]] = {}
    for row in rows:
        part = part_map.get(row.part_id) if row.part_id else None
        profile = profile_map.get(row.part_id) if row.part_id else None
        result.setdefault(row.template_item_id, []).append(
            VehicleServiceTemplatePartResponse(
                id=row.id,
                template_item_id=row.template_item_id,
                part_id=row.part_id,
                part_no=row.part_no or (part.part_no if part else None),
                part_name=row.part_name or (part.name if part else ""),
                qty=row.qty,
                unit_price=row.unit_price if row.unit_price is not None else (profile.sale_price if profile else None),
                notes=row.notes,
                sort_order=row.sort_order,
                is_optional=row.is_optional,
            ).model_dump()
        )
    return result


def _service_item_to_response(
    row: VehicleServiceTemplateItem,
    profile: VehicleServiceTemplateProfile | None,
    required_parts: list[dict] | None = None,
) -> dict:
    return VehicleServiceTemplateItemResponse(
        id=row.id,
        model_id=row.model_id,
        service_name=row.part_name,
        service_code=row.part_code,
        repair_method=row.repair_method,
        labor_hours=row.labor_hours,
        labor_price=profile.labor_price if profile else None,
        suggested_price=profile.suggested_price if profile else None,
        notes=row.notes,
        sort_order=row.sort_order,
        is_active=row.is_active,
        required_parts=required_parts or [],
    ).model_dump()


def _upsert_service_required_parts(
    db: Session,
    template_item_id: int,
    required_parts: list[VehicleServiceTemplatePartCreate],
):
    db.query(VehicleServiceTemplatePart).filter(
        VehicleServiceTemplatePart.template_item_id == template_item_id
    ).delete(synchronize_session=False)
    for index, item in enumerate(required_parts, start=1):
        payload = item.model_dump()
        db.add(
            VehicleServiceTemplatePart(
                template_item_id=template_item_id,
                part_id=payload.get("part_id"),
                part_no=payload.get("part_no"),
                part_name=payload["part_name"],
                qty=payload["qty"],
                unit_price=payload.get("unit_price"),
                notes=payload.get("notes"),
                sort_order=payload.get("sort_order") or (index * 10),
                is_optional=payload.get("is_optional", False),
            )
        )


def _serialize_service_item_map(db: Session, item_ids: list[int]) -> dict[int, dict]:
    if not item_ids:
        return {}
    rows = db.query(VehicleServiceTemplateItem).filter(VehicleServiceTemplateItem.id.in_(item_ids)).all()
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile).filter(
            VehicleServiceTemplateProfile.template_item_id.in_(item_ids)
        ).all()
    }
    parts_map = _serialize_service_required_parts(db, item_ids)
    return {
        row.id: _service_item_to_response(row, profile_map.get(row.id), parts_map.get(row.id, []))
        for row in rows
    }


def _serialize_service_package_items(db: Session, package_ids: list[int]) -> dict[int, list[dict]]:
    if not package_ids:
        return {}
    rows = (
        db.query(VehicleServicePackageItem)
        .filter(VehicleServicePackageItem.package_id.in_(package_ids))
        .order_by(VehicleServicePackageItem.sort_order.asc(), VehicleServicePackageItem.id.asc())
        .all()
    )
    service_item_map = _serialize_service_item_map(db, [row.template_item_id for row in rows])
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row.package_id, []).append(
            VehicleServicePackageItemResponse(
                id=row.id,
                package_id=row.package_id,
                template_item_id=row.template_item_id,
                sort_order=row.sort_order,
                is_optional=row.is_optional,
                notes=row.notes,
                service_item=service_item_map.get(row.template_item_id),
            ).model_dump()
        )
    return result


def _service_package_to_response(row: VehicleServicePackage, items: list[dict] | None = None) -> dict:
    return VehicleServicePackageResponse(
        id=row.id,
        model_id=row.model_id,
        package_name=row.package_name,
        package_code=row.package_code,
        description=row.description,
        recommended_interval_km=row.recommended_interval_km,
        recommended_interval_months=row.recommended_interval_months,
        labor_hours_total=row.labor_hours_total,
        labor_price_total=row.labor_price_total,
        parts_price_total=row.parts_price_total,
        suggested_price_total=row.suggested_price_total,
        sort_order=row.sort_order,
        is_active=row.is_active,
        items=items or [],
    ).model_dump()


def _recalculate_service_package_totals(db: Session, package: VehicleServicePackage):
    summary = (
        db.query(
            func.coalesce(func.sum(VehicleServiceTemplateItem.labor_hours), 0.0),
            func.coalesce(func.sum(VehicleServiceTemplateProfile.labor_price), 0.0),
            func.coalesce(func.sum(VehicleServiceTemplateProfile.suggested_price), 0.0),
        )
        .select_from(VehicleServicePackageItem)
        .join(VehicleServiceTemplateItem, VehicleServiceTemplateItem.id == VehicleServicePackageItem.template_item_id)
        .outerjoin(
            VehicleServiceTemplateProfile,
            VehicleServiceTemplateProfile.template_item_id == VehicleServiceTemplateItem.id,
        )
        .filter(VehicleServicePackageItem.package_id == package.id)
        .first()
    )
    parts_total = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(VehicleServiceTemplatePart.unit_price, 0.0) * func.coalesce(VehicleServiceTemplatePart.qty, 0.0)
                ),
                0.0,
            )
        )
        .select_from(VehicleServicePackageItem)
        .join(VehicleServiceTemplatePart, VehicleServiceTemplatePart.template_item_id == VehicleServicePackageItem.template_item_id)
        .filter(VehicleServicePackageItem.package_id == package.id)
        .scalar()
        or 0.0
    )
    labor_hours_total = float(summary[0] or 0.0) if summary else 0.0
    labor_price_total = float(summary[1] or 0.0) if summary else 0.0
    suggested_price_total = float(summary[2] or 0.0) if summary else 0.0
    parts_price_total = float(parts_total or 0.0)
    values = {
        "labor_hours_total": round(labor_hours_total, 2),
        "labor_price_total": round(labor_price_total, 2),
        "parts_price_total": round(parts_price_total, 2),
        "suggested_price_total": round(max(suggested_price_total, labor_price_total + parts_price_total), 2),
    }
    db.query(VehicleServicePackage).filter(VehicleServicePackage.id == package.id).update(values, synchronize_session=False)
    for key, value in values.items():
        setattr(package, key, value)


def _upsert_service_package_items(db: Session, package_id: int, items: list[VehicleServicePackageItemCreate]):
    db.query(VehicleServicePackageItem).filter(
        VehicleServicePackageItem.package_id == package_id
    ).delete(synchronize_session=False)
    for index, item in enumerate(items, start=1):
        payload = item.model_dump()
        db.add(
            VehicleServicePackageItem(
                package_id=package_id,
                template_item_id=payload["template_item_id"],
                sort_order=payload.get("sort_order") or (index * 10),
                is_optional=payload.get("is_optional", False),
                notes=payload.get("notes"),
            )
        )


def _ensure_baseline_service_packages_for_model(db: Session, model_id: int) -> int:
    service_items = (
        db.query(VehicleServiceTemplateItem)
        .filter(VehicleServiceTemplateItem.model_id == model_id, VehicleServiceTemplateItem.is_active.is_(True))
        .all()
    )
    service_code_map = {str(item.part_code or "").upper(): item for item in service_items if item.part_code}
    created = 0
    for spec in BASELINE_SERVICE_PACKAGE_SPECS:
        exists = (
            db.query(VehicleServicePackage.id)
            .filter(
                VehicleServicePackage.model_id == model_id,
                VehicleServicePackage.package_code == spec["package_code"],
            )
            .first()
        )
        if exists:
            continue
        selected_items = [service_code_map.get(code) for code in spec["service_codes"] if service_code_map.get(code)]
        if not selected_items:
            continue
        row = VehicleServicePackage(
            model_id=model_id,
            package_code=spec["package_code"],
            package_name=spec["package_name"],
            description=spec["description"],
            recommended_interval_km=spec.get("recommended_interval_km"),
            recommended_interval_months=spec.get("recommended_interval_months"),
            sort_order=spec.get("sort_order") or ((created + 1) * 10),
            is_active=True,
        )
        db.add(row)
        db.flush()
        _upsert_service_package_items(
            db,
            row.id,
            [
                VehicleServicePackageItemCreate(template_item_id=item.id, sort_order=(index + 1) * 10)
                for index, item in enumerate(selected_items)
            ],
        )
        db.flush()
        _recalculate_service_package_totals(db, row)
        created += 1
    return created


_SERVICE_MANUAL_PART_RULES = {
    "PM-OIL": {
        "service_terms": ["更换机油", "发动机机油", "机油"],
        "part_aliases": [
            {"terms": ["10w40", "10w-40", "4t机油", "发动机机油"], "preferred_part_no": "OIL-10W40-1L", "fallback_part_no": "GEN-OIL-10W40", "qty": 1},
        ],
    },
    "PM-OIL-FILTER": {
        "service_terms": ["更换机油+机滤", "发动机机油", "机油滤芯", "机滤"],
        "part_aliases": [
            {"terms": ["10w40", "10w-40", "4t机油", "发动机机油"], "preferred_part_no": "OIL-10W40-1L", "fallback_part_no": "GEN-OIL-10W40", "qty": 1},
            {"terms": ["机油滤芯", "机滤", "oil filter"], "preferred_part_no": "OIL-FLTR-UNIV", "fallback_part_no": "GEN-OIL-FILTER", "qty": 1},
        ],
    },
    "PM-BRAKE-FLUID": {
        "service_terms": ["更换刹车油", "刹车油", "制动液", "制动液液位"],
        "part_aliases": [
            {"terms": ["dot4", "刹车油", "制动液"], "preferred_part_no": "BRK-FLUID-DOT4", "fallback_part_no": "GEN-BRAKE-FLUID-DOT4", "qty": 1},
        ],
    },
    "PM-AIR-FILTER": {
        "service_terms": ["更换空气滤芯", "空气滤清器", "空气滤芯"],
        "part_aliases": [
            {"terms": ["空气滤清器", "空气滤芯", "air filter"], "preferred_part_no": "AIR-FLTR-UNIV", "fallback_part_no": "GEN-AIR-FILTER", "qty": 1},
        ],
    },
    "PM-SPARK-PLUG": {
        "service_terms": ["更换火花塞", "火花塞"],
        "part_aliases": [
            {"terms": ["cr8e", "火花塞", "spark plug"], "preferred_part_no": "SPARK-CR8E", "fallback_part_no": "GEN-SPARK-PLUG", "qty": 1},
        ],
    },
    "PM-CHAIN-SERVICE": {
        "service_terms": ["链条清洁保养", "链条", "驱动链"],
        "part_aliases": [
            {"terms": ["链条", "润滑", "链条清洁", "链条润滑"], "preferred_part_no": "GEN-CHAIN-LUBE", "fallback_part_no": "GEN-CHAIN-LUBE", "qty": 1},
        ],
    },
    "PM-COOLANT": {
        "service_terms": ["更换冷却液", "冷却液", "冷却系统"],
        "part_aliases": [
            {"terms": ["冷却液", "coolant"], "preferred_part_no": "COOLANT-1L", "fallback_part_no": "GEN-COOLANT", "qty": 1},
        ],
    },
    "PM-FRONT-BRAKE-PADS": {
        "service_terms": ["更换前刹车片", "前刹车片", "前制动"],
        "part_aliases": [
            {"terms": ["前刹车片", "前制动", "front brake pad"], "preferred_part_no": "PAD-FR-STD", "fallback_part_no": "GEN-FRONT-BRAKE-PADS", "qty": 1},
        ],
    },
    "PM-REAR-BRAKE-PADS": {
        "service_terms": ["更换后刹车片", "后刹车片", "后制动"],
        "part_aliases": [
            {"terms": ["后刹车片", "后制动", "rear brake pad"], "preferred_part_no": "PAD-RR-STD", "fallback_part_no": "GEN-REAR-BRAKE-PADS", "qty": 1},
        ],
    },
}


def _normalize_match_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _service_item_rule(service_item: VehicleServiceTemplateItem) -> dict:
    key = str(service_item.part_code or "").strip().upper()
    if key and key in _SERVICE_MANUAL_PART_RULES:
        return _SERVICE_MANUAL_PART_RULES[key]
    service_name = str(service_item.part_name or "")
    for candidate_key, rule in _SERVICE_MANUAL_PART_RULES.items():
        if any(term in service_name for term in rule["service_terms"]):
            return rule
    return {
        "service_terms": [service_name] if service_name else [],
        "part_aliases": [],
    }


def _collect_service_manual_hits(
    service_item: VehicleServiceTemplateItem,
    segments: list[VehicleKnowledgeSegment],
    procedure_steps_map: dict[int, list[ProcedureStep]],
) -> list[dict]:
    rule = _service_item_rule(service_item)
    service_terms = [term for term in rule["service_terms"] if term]
    hits: list[dict] = []
    for segment in segments:
        title = str(segment.title or "")
        notes = str(segment.notes or "")
        procedure = getattr(segment, "_procedure", None)
        steps = procedure_steps_map.get(segment.procedure_id, []) if segment.procedure_id else []
        haystack = " ".join(
            [title, notes, getattr(procedure, "name", ""), getattr(procedure, "description", "")]
            + [step.instruction or "" for step in steps]
            + [step.required_tools or "" for step in steps]
        )
        score = 0
        matched_terms: list[str] = []
        for term in service_terms:
            if term and term in haystack:
                matched_terms.append(term)
                score += 4 if term in title else 2
        if service_item.part_name and service_item.part_name in title:
            score += 6
        if procedure and service_item.part_name and service_item.part_name in str(procedure.name or ""):
            score += 5
        if score <= 0:
            continue
        hits.append(
            {
                "segment": segment,
                "procedure": procedure,
                "steps": steps,
                "score": score,
                "matched_terms": matched_terms,
                "haystack": haystack,
            }
        )
    return sorted(hits, key=lambda item: (-item["score"], int(item["segment"].start_page or 0)))


def _append_model_compatibility(part: PartCatalogItem, model_id: int):
    compatible = [int(item) for item in (part.compatible_model_ids or []) if str(item).isdigit()]
    if model_id not in compatible:
        compatible.append(model_id)
        part.compatible_model_ids = compatible


def _choose_part_candidate(
    parts_by_no: dict[str, PartCatalogItem],
    all_parts: list[PartCatalogItem],
    alias_spec: dict,
    evidence_text: str,
    model_id: int,
) -> PartCatalogItem | None:
    evidence_norm = _normalize_match_text(evidence_text)
    preferred_no = alias_spec.get("preferred_part_no")
    fallback_no = alias_spec.get("fallback_part_no")
    if preferred_no and preferred_no in parts_by_no:
        return parts_by_no[preferred_no]
    ranked: list[tuple[int, PartCatalogItem]] = []
    alias_terms = alias_spec.get("terms") or []
    for part in all_parts:
        if not part.is_active:
            continue
        score = 0
        part_no_norm = _normalize_match_text(part.part_no)
        name_norm = _normalize_match_text(part.name)
        compatible = set(int(item) for item in (part.compatible_model_ids or []) if str(item).isdigit())
        if model_id in compatible:
            score += 3
        if fallback_no and part.part_no == fallback_no:
            score += 2
        for term in alias_terms:
            term_norm = _normalize_match_text(term)
            if term_norm and term_norm in evidence_norm:
                if term_norm in part_no_norm:
                    score += 6
                if term_norm in name_norm:
                    score += 5
            if term and term in part.name:
                score += 4
        if score > 0:
            if str(part.part_no or "").startswith("GEN-"):
                score -= 2
            ranked.append((score, part))
    if ranked:
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        return ranked[0][1]
    if fallback_no and fallback_no in parts_by_no:
        return parts_by_no[fallback_no]
    return None


def _build_required_part_note(
    service_item: VehicleServiceTemplateItem,
    part: PartCatalogItem,
    hits: list[dict],
    alias_spec: dict,
) -> str:
    top_hits = hits[:3]
    pages = []
    chapters = []
    for item in top_hits:
        segment = item["segment"]
        page_label = f"{segment.start_page}-{segment.end_page}" if segment.end_page and segment.end_page != segment.start_page else f"{segment.start_page}"
        if page_label not in pages:
            pages.append(page_label)
        title = str(segment.title or "").strip()
        if title and title not in chapters:
            chapters.append(title)
    hint_terms = [item for item in (alias_spec.get("terms") or []) if item]
    hints = " / ".join(hint_terms[:3])
    chapter_text = "；".join(chapters[:3]) if chapters else service_item.part_name
    page_text = "、".join([f"第{page}页" for page in pages[:3]]) if pages else "页码待补充"
    return f"手册自动同步：{chapter_text}；来源 {page_text}；匹配到配件 {part.part_no} {part.name}" + (f"；依据 {hints}" if hints else "")


def _sync_service_item_required_parts_from_manual(
    db: Session,
    model_id: int,
    *,
    service_item_ids: list[int] | None = None,
) -> list[dict]:
    q = db.query(VehicleServiceTemplateItem).filter(
        VehicleServiceTemplateItem.model_id == model_id,
        VehicleServiceTemplateItem.is_active.is_(True),
    )
    if service_item_ids:
        q = q.filter(VehicleServiceTemplateItem.id.in_(service_item_ids))
    service_items = q.order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc()).all()
    if not service_items:
        return []

    segments = (
        db.query(VehicleKnowledgeSegment)
        .filter(VehicleKnowledgeSegment.model_id == model_id)
        .order_by(VehicleKnowledgeSegment.start_page.asc(), VehicleKnowledgeSegment.id.asc())
        .all()
    )
    procedure_ids = [item.procedure_id for item in segments if item.procedure_id]
    procedure_map = {}
    if procedure_ids:
        for proc in db.query(Procedure).filter(Procedure.id.in_(procedure_ids)).all():
            procedure_map[proc.id] = proc
    for segment in segments:
        setattr(segment, "_procedure", procedure_map.get(segment.procedure_id))
    steps_map: dict[int, list[ProcedureStep]] = {}
    if procedure_ids:
        for step in (
            db.query(ProcedureStep)
            .filter(ProcedureStep.procedure_id.in_(procedure_ids))
            .order_by(ProcedureStep.procedure_id.asc(), ProcedureStep.step_order.asc(), ProcedureStep.id.asc())
            .all()
        ):
            steps_map.setdefault(step.procedure_id, []).append(step)

    all_parts = db.query(PartCatalogItem).filter(PartCatalogItem.is_active.is_(True)).all()
    parts_by_no = {part.part_no: part for part in all_parts}
    results: list[dict] = []
    for service_item in service_items:
        rule = _service_item_rule(service_item)
        hits = _collect_service_manual_hits(service_item, segments, steps_map)
        evidence_text = " ".join(
            [
                service_item.part_name or "",
                service_item.part_code or "",
                service_item.repair_method or "",
                service_item.notes or "",
            ]
            + [item["haystack"] for item in hits[:5]]
        )
        parts_payload: list[VehicleServiceTemplatePartCreate] = []
        for index, alias_spec in enumerate(rule.get("part_aliases") or [], start=1):
            matched_part = _choose_part_candidate(parts_by_no, all_parts, alias_spec, evidence_text, model_id)
            if not matched_part:
                continue
            _append_model_compatibility(matched_part, model_id)
            note = _build_required_part_note(service_item, matched_part, hits, alias_spec)
            profile = _ensure_part_profile(db, matched_part.id)
            parts_payload.append(
                VehicleServiceTemplatePartCreate(
                    part_id=matched_part.id,
                    part_no=matched_part.part_no,
                    part_name=matched_part.name,
                    qty=float(alias_spec.get("qty") or 1),
                    unit_price=profile.sale_price,
                    notes=note,
                    sort_order=index * 10,
                    is_optional=bool(alias_spec.get("is_optional", False)),
                )
            )
        if not parts_payload:
            existing_parts_map = _serialize_service_required_parts(db, [service_item.id])
            results.append(
                {
                    "service_item_id": service_item.id,
                    "service_name": service_item.part_name,
                    "updated": False,
                    "required_parts": existing_parts_map.get(service_item.id, []),
                    "matched_segments": [],
                }
            )
            continue
        _upsert_service_required_parts(db, service_item.id, parts_payload)
        results.append(
            {
                "service_item_id": service_item.id,
                "service_name": service_item.part_name,
                "updated": True,
                "required_parts": [item.model_dump() for item in parts_payload],
                "matched_segments": [
                    {
                        "segment_id": item["segment"].id,
                        "title": item["segment"].title,
                        "start_page": item["segment"].start_page,
                        "end_page": item["segment"].end_page,
                    }
                    for item in hits[:5]
                ],
            }
        )
    db.flush()
    return results

def _sync_default_catalog(db: Session) -> dict:
    vehicle_added = 0
    part_added = 0

    for item in DEFAULT_VEHICLE_MODELS:
        year_to = item.get("year_to") or item["year_from"]
        exists = (
            db.query(VehicleCatalogModel.id)
            .filter(
                VehicleCatalogModel.brand == item["brand"],
                VehicleCatalogModel.model_name == item["model_name"],
                VehicleCatalogModel.year_from == item["year_from"],
                VehicleCatalogModel.year_to == year_to,
            )
            .first()
        )


def _ensure_baseline_parts(db: Session) -> dict[str, PartCatalogItem]:
    part_map: dict[str, PartCatalogItem] = {}
    for spec in BASELINE_PART_SPECS:
        row = db.query(PartCatalogItem).filter(PartCatalogItem.part_no == spec["part_no"]).first()
        if not row:
            row = PartCatalogItem(
                part_no=spec["part_no"],
                name=spec["name"],
                category=spec["category"],
                unit=spec["unit"],
                is_active=True,
            )
            db.add(row)
            db.flush()
        profile = _ensure_part_profile(db, row.id)
        profile.sale_price = spec["sale_price"]
        profile.cost_price = spec["cost_price"]
        part_map[spec["part_no"]] = row
    return part_map


def _ensure_baseline_service_items_for_model(
    db: Session,
    model_id: int,
    *,
    part_map: dict[str, PartCatalogItem] | None = None,
    default_labor_price: float | None = None,
) -> int:
    part_map = part_map or _ensure_baseline_parts(db)
    created_count = 0
    for spec in BASELINE_SERVICE_SPECS:
        exists = (
            db.query(VehicleServiceTemplateItem.id)
            .filter(
                VehicleServiceTemplateItem.model_id == model_id,
                VehicleServiceTemplateItem.part_code == spec["service_code"],
            )
            .first()
        )
        if exists:
            continue
        row = VehicleServiceTemplateItem(
            model_id=model_id,
            part_name=spec["service_name"],
            part_code=spec["service_code"],
            repair_method=spec["repair_method"],
            labor_hours=spec["labor_hours"],
            sort_order=created_count * 10 + 10,
            is_active=True,
        )
        db.add(row)
        db.flush()
        profile = _ensure_service_profile(db, row.id)
        profile.labor_price = float(default_labor_price) if default_labor_price is not None else spec["labor_price"]
        profile.suggested_price = spec["suggested_price"]
        required_parts: list[VehicleServiceTemplatePartCreate] = []
        for item in spec["required_parts"]:
            part_row = part_map.get(item["part_no"])
            required_parts.append(
                VehicleServiceTemplatePartCreate(
                    part_id=part_row.id if part_row else None,
                    part_no=item["part_no"],
                    part_name=item["part_name"],
                    qty=item["qty"],
                    unit_price=None,
                    sort_order=item["sort_order"],
                    notes=None,
                    is_optional=False,
                )
            )
        _upsert_service_required_parts(db, row.id, required_parts)
        created_count += 1
    return created_count


def _resolve_store_default_labor_price(db: Session, store_id: str | None) -> float | None:
    normalized_store_id = compact_spaces(store_id or "").lower() or "default"
    row = (
        db.query(AppSetting)
        .filter(AppSetting.store_id == normalized_store_id)
        .order_by(AppSetting.id.desc())
        .first()
    )
    if not row or row.default_labor_price is None:
        return None
    return float(row.default_labor_price)


def _ensure_baseline_service_items_for_all_models(db: Session, *, default_labor_price: float | None = None) -> dict:
    part_map = _ensure_baseline_parts(db)
    created = 0
    model_ids = [row[0] for row in db.query(VehicleCatalogModel.id).all()]
    for model_id in model_ids:
        created += _ensure_baseline_service_items_for_model(
            db,
            model_id,
            part_map=part_map,
            default_labor_price=default_labor_price,
        )
    db.commit()
    return {"models": len(model_ids), "service_items_created": created}


def _sync_default_catalog(db: Session) -> dict:
    vehicle_added = 0
    part_added = 0

    for item in DEFAULT_VEHICLE_MODELS:
        year_to = item.get("year_to") or item["year_from"]
        exists = (
            db.query(VehicleCatalogModel.id)
            .filter(
                VehicleCatalogModel.brand == item["brand"],
                VehicleCatalogModel.model_name == item["model_name"],
                VehicleCatalogModel.year_from == item["year_from"],
                VehicleCatalogModel.year_to == year_to,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            VehicleCatalogModel(
                brand=item["brand"],
                model_name=item["model_name"],
                year_from=item["year_from"],
                year_to=year_to,
                displacement_cc=item.get("displacement_cc"),
                category=item.get("category"),
                fuel_type=item.get("fuel_type") or "gasoline",
                default_engine_code=item.get("default_engine_code"),
                source="seed_global_mainstream_2011_2026",
                is_active=True,
            )
        )
        vehicle_added += 1

    for item in DEFAULT_PART_ITEMS:
        db_part = (
            db.query(PartCatalogItem)
            .filter(PartCatalogItem.part_no == item["part_no"])
            .first()
        )
        if not db_part:
            db_part = PartCatalogItem(
                part_no=item["part_no"],
                name=item["name"],
                brand=item.get("brand"),
                category=item.get("category"),
                unit=item.get("unit") or "件",
                compatible_model_ids=item.get("compatible_model_ids") or [],
                min_stock=item.get("min_stock"),
                is_active=True,
            )
            db.add(db_part)
            db.flush()
            part_added += 1
        _ensure_part_profile(db, db_part.id)

    baseline_result = _ensure_baseline_service_items_for_all_models(db)
    return {
        "vehicle_added": vehicle_added,
        "part_added": part_added,
        "baseline_service_items_created": baseline_result["service_items_created"],
    }


def _sync_58moto_catalog(
    db: Session,
    *,
    max_brands: int = 0,
    brand_keyword: str = "",
    only_on_sale: bool = True,
    include_detail: bool = True,
) -> dict:
    today = datetime.now()
    default_year_from = max(1950, today.year - 15)
    default_year_to = today.year
    source = f"58moto_api_{today.strftime('%Y%m%d')}"

    brand_payload = _fetch_moto58_json("/carport/brand/v2/all/list")
    raw_brands = brand_payload.get("data") or []
    keyword = (brand_keyword or "").strip().lower()

    brands: list[dict] = []
    for row in raw_brands:
        if only_on_sale and int(row.get("existSaleGoods") or 0) != 1:
            continue
        name = (row.get("brandName") or "").strip()
        if not name:
            continue
        if keyword and keyword not in name.lower() and keyword not in (row.get("keywords") or "").lower():
            continue
        brand_id = _to_int(row.get("brandId"))
        if not brand_id:
            continue
        brands.append({"brand_id": brand_id, "brand_name": name})

    brands = sorted(brands, key=lambda item: (item["brand_name"], item["brand_id"]))
    if max_brands > 0:
        brands = brands[:max_brands]

    inserted = 0
    existed = 0
    failed_brands = 0
    failed_models = 0
    processed_goods = 0
    touched_brands = 0

    for brand in brands:
        touched_brands += 1
        try:
            goods_payload = _fetch_moto58_json(
                f"/carport/goods/v6/brand/{brand['brand_id']}",
                params={"onSale": 1 if only_on_sale else "", "rows": 500},
            )
        except Exception:
            failed_brands += 1
            continue

        goods = goods_payload.get("data") or []
        if not isinstance(goods, list):
            continue
        processed_goods += len(goods)

        for item in goods:
            try:
                model_name = (item.get("goodName") or "").strip()
                if not model_name:
                    continue

                category = (item.get("seriesName") or "").strip() or None
                displacement_cc = _extract_displacement_cc(item.get("goodVolume"), model_name)
                year_from = default_year_from
                year_to = default_year_to

                if include_detail:
                    good_id = _to_int(item.get("goodId"))
                    if good_id:
                        detail_payload = _fetch_moto58_json(f"/carport/goods/info/v3/detail/{good_id}")
                        detail = detail_payload.get("data") or {}
                        car_list = detail.get("carList") or []
                        years = _extract_years(model_name, detail.get("carName"), detail.get("goodTime"))
                        for group in car_list if isinstance(car_list, list) else []:
                            if not isinstance(group, dict):
                                continue
                            years.extend(_extract_years(group.get("name")))
                            for info in group.get("carInfoList") or []:
                                if not isinstance(info, dict):
                                    continue
                                years.extend(
                                    _extract_years(
                                        info.get("carName"),
                                        info.get("goodsCarName"),
                                        info.get("goodTime"),
                                    )
                                )
                                if not displacement_cc:
                                    displacement_cc = _extract_displacement_cc(
                                        info.get("goodVolume"),
                                        info.get("goodsCarName"),
                                    )
                        if years:
                            year_from = min(years)
                            year_to = max(years)

                exists = (
                    db.query(VehicleCatalogModel.id)
                    .filter(
                        VehicleCatalogModel.brand == brand["brand_name"],
                        VehicleCatalogModel.model_name == model_name,
                        VehicleCatalogModel.year_from == year_from,
                        VehicleCatalogModel.year_to == year_to,
                    )
                    .first()
                )
                if exists:
                    existed += 1
                    continue

                db.add(
                    VehicleCatalogModel(
                        brand=brand["brand_name"],
                        model_name=model_name,
                        year_from=year_from,
                        year_to=year_to,
                        displacement_cc=displacement_cc,
                        category=category,
                        fuel_type="gasoline",
                        source=source,
                        is_active=True,
                    )
                )
                inserted += 1
            except Exception:
                failed_models += 1
                continue

    db.commit()
    return {
        "inserted": inserted,
        "existed": existed,
        "failed_brands": failed_brands,
        "failed_models": failed_models,
        "processed_goods": processed_goods,
        "touched_brands": touched_brands,
    }


def _seed_default_catalog_if_needed(db: Session):
    if not db.query(VehicleCatalogModel.id).limit(1).first() or not db.query(PartCatalogItem.id).limit(1).first():
        _sync_default_catalog(db)


@router.post("/seed-defaults")
async def seed_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    return {"seeded": True, **_sync_default_catalog(db)}


@router.post("/sync-defaults")
async def sync_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    return {"synced": True, **_sync_default_catalog(db)}


@router.post("/seed-baseline-services")
async def seed_baseline_services(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    _ = current_user
    store_id = request.headers.get("X-Store-Id") or "default"
    default_labor_price = _resolve_store_default_labor_price(db, store_id)
    return {
        "seeded": True,
        "default_labor_price": default_labor_price,
        **_ensure_baseline_service_items_for_all_models(db, default_labor_price=default_labor_price),
    }

@router.post("/sync-58moto")
async def sync_58moto(
    max_brands: int = Query(0, ge=0, le=2000),
    brand_keyword: str = "",
    only_on_sale: bool = True,
    include_detail: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    try:
        result = _sync_58moto_catalog(
            db,
            max_brands=max_brands,
            brand_keyword=brand_keyword,
            only_on_sale=only_on_sale,
            include_detail=include_detail,
        )
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"sync failed from 58moto: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"sync failed: {exc}") from exc
    return {"synced": True, **result}


@router.get("/vehicle-models/brands", response_model=list[str])
async def list_vehicle_brands(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    query = db.query(VehicleCatalogModel.brand).distinct()
    if active_only:
        query = query.filter(VehicleCatalogModel.is_active.is_(True))
    return [row[0] for row in query.order_by(VehicleCatalogModel.brand.asc()).all() if row[0]]


@router.get("/vehicle-models/categories", response_model=list[str])
async def list_vehicle_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    query = (
        db.query(VehicleCatalogModel.category)
        .filter(VehicleCatalogModel.category.isnot(None))
        .filter(func.length(VehicleCatalogModel.category) > 0)
    )
    if active_only:
        query = query.filter(VehicleCatalogModel.is_active.is_(True))
    return [row[0] for row in query.distinct().order_by(VehicleCatalogModel.category.asc()).all() if row[0]]


@router.get("/vehicle-models/by-brand", response_model=list[dict])
async def list_vehicle_models_by_brand(
    brand: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    q = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.brand == brand)
    if active_only:
        q = q.filter(VehicleCatalogModel.is_active.is_(True))
    rows = q.order_by(VehicleCatalogModel.model_name.asc(), VehicleCatalogModel.year_from.desc()).all()
    return [
        {
            "id": row.id,
            "brand": row.brand,
            "model_name": row.model_name,
            "year_from": row.year_from,
            "year_to": row.year_to,
            "category": row.category,
            "displacement_cc": row.displacement_cc,
            "default_engine_code": row.default_engine_code,
        }
        for row in rows
    ]


@router.get("/vehicle-models", response_model=dict)
async def list_vehicle_models(
    brand: str = "",
    category: str = "",
    model_name: str = "",
    keyword: str = "",
    year: int | None = Query(None, ge=1950, le=2100),
    active_only: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    q = db.query(VehicleCatalogModel)
    if active_only:
        q = q.filter(VehicleCatalogModel.is_active.is_(True))
    if brand:
        q = q.filter(VehicleCatalogModel.brand == brand)
    if category:
        q = q.filter(VehicleCatalogModel.category == category)
    if model_name:
        q = q.filter(VehicleCatalogModel.model_name == model_name)
    if keyword:
        q = q.filter(
            or_(
                VehicleCatalogModel.brand.ilike(f"%{keyword}%"),
                VehicleCatalogModel.model_name.ilike(f"%{keyword}%"),
                VehicleCatalogModel.category.ilike(f"%{keyword}%"),
            )
        )
    if year is not None:
        q = q.filter(VehicleCatalogModel.year_from <= year, VehicleCatalogModel.year_to >= year)
    if keyword:
        candidates = q.all()
        ranked = sorted(
            candidates,
            key=lambda row: _rank_vehicle_model(row, keyword),
            reverse=True,
        )
        total = len(ranked)
        rows = ranked[(page - 1) * size:(page - 1) * size + size]
    else:
        total = q.count()
        rows = (
            q.order_by(
                VehicleCatalogModel.brand.asc(),
                VehicleCatalogModel.model_name.asc(),
                VehicleCatalogModel.year_from.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
    items = [
        VehicleCatalogModelResponse(
            id=row.id,
            brand=row.brand,
            model_name=row.model_name,
            year_from=row.year_from,
            year_to=row.year_to,
            displacement_cc=row.displacement_cc,
            category=row.category,
            fuel_type=row.fuel_type,
            default_engine_code=row.default_engine_code,
            source=row.source,
            is_active=row.is_active,
        ).model_dump()
        for row in rows
    ]
    return {"items": items, "page": page, "size": size, "total": total, "has_more": (page * size) < total}


@router.post("/vehicle-models", response_model=VehicleCatalogModelResponse)
async def create_vehicle_model(
    payload: VehicleCatalogModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = VehicleCatalogModel(
        brand=payload.brand,
        model_name=payload.model_name,
        year_from=payload.year_from,
        year_to=_normalize_year_to(payload.year_from, payload.year_to),
        displacement_cc=payload.displacement_cc,
        category=payload.category,
        fuel_type=payload.fuel_type,
        default_engine_code=payload.default_engine_code,
        source=payload.source,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _ensure_baseline_service_items_for_model(db, row.id)
    db.commit()
    return row


@router.put("/vehicle-models/{model_id}", response_model=VehicleCatalogModelResponse)
async def update_vehicle_model(
    model_id: int,
    payload: VehicleCatalogModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    for key, value in patch.items():
        setattr(row, key, value)
    row.year_to = _normalize_year_to(row.year_from, row.year_to)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/vehicle-models/{model_id}")
async def delete_vehicle_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    item_ids = [item.id for item in db.query(VehicleServiceTemplateItem).filter(VehicleServiceTemplateItem.model_id == model_id).all()]
    if item_ids:
        db.query(VehicleServiceTemplatePart).filter(VehicleServiceTemplatePart.template_item_id.in_(item_ids)).delete(synchronize_session=False)
        db.query(VehicleServiceTemplateProfile).filter(VehicleServiceTemplateProfile.template_item_id.in_(item_ids)).delete(synchronize_session=False)
        db.query(VehicleServiceTemplateItem).filter(VehicleServiceTemplateItem.model_id == model_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": model_id}


@router.get("/vehicle-models/{model_id}/specs", response_model=list[VehicleCatalogSpecResponse])
async def list_vehicle_model_specs(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    rows = (
        db.query(VehicleCatalogSpec)
        .filter(VehicleCatalogSpec.model_id == model_id)
        .order_by(VehicleCatalogSpec.spec_label.asc(), VehicleCatalogSpec.id.asc())
        .all()
    )
    return rows


@router.post("/vehicle-models/{model_id}/specs", response_model=VehicleCatalogSpecResponse)
async def create_vehicle_model_spec(
    model_id: int,
    payload: VehicleCatalogSpecPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    spec_key = (payload.spec_key or "").strip()
    spec_label = (payload.spec_label or "").strip()
    if not spec_key or not spec_label:
        raise HTTPException(status_code=400, detail="spec_key and spec_label are required")
    row = VehicleCatalogSpec(
        model_id=model_id,
        spec_key=spec_key,
        spec_label=spec_label,
        spec_type=(payload.spec_type or "").strip() or None,
        spec_value=(payload.spec_value or "").strip() or None,
        spec_unit=(payload.spec_unit or "").strip() or None,
        source_page=(payload.source_page or "").strip() or None,
        source_text=(payload.source_text or "").strip() or None,
        review_status=(payload.review_status or "confirmed").strip() or "confirmed",
        source=(payload.source or "manual").strip() or "manual",
        notes=(payload.notes or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/vehicle-models/{model_id}/specs/{spec_id}", response_model=VehicleCatalogSpecResponse)
async def update_vehicle_model_spec(
    model_id: int,
    spec_id: int,
    payload: VehicleCatalogSpecPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleCatalogSpec)
        .filter(VehicleCatalogSpec.id == spec_id, VehicleCatalogSpec.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle spec not found")
    row.spec_key = (payload.spec_key or "").strip() or row.spec_key
    row.spec_label = (payload.spec_label or "").strip() or row.spec_label
    row.spec_type = (payload.spec_type or "").strip() or None
    row.spec_value = (payload.spec_value or "").strip() or None
    row.spec_unit = (payload.spec_unit or "").strip() or None
    row.source_page = (payload.source_page or "").strip() or None
    row.source_text = (payload.source_text or "").strip() or None
    row.review_status = (payload.review_status or "confirmed").strip() or "confirmed"
    row.source = (payload.source or row.source or "manual").strip() or "manual"
    row.notes = (payload.notes or "").strip() or None
    db.commit()
    db.refresh(row)
    return row


@router.delete("/vehicle-models/{model_id}/specs/{spec_id}")
async def delete_vehicle_model_spec(
    model_id: int,
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleCatalogSpec)
        .filter(VehicleCatalogSpec.id == spec_id, VehicleCatalogSpec.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle spec not found")
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": spec_id, "model_id": model_id}

@router.get("/vehicle-models/{model_id}/service-items", response_model=list[VehicleServiceTemplateItemResponse])
async def list_vehicle_service_items(
    model_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")

    q = db.query(VehicleServiceTemplateItem).filter(VehicleServiceTemplateItem.model_id == model_id)
    if active_only:
        q = q.filter(VehicleServiceTemplateItem.is_active.is_(True))
    rows = q.order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc()).all()
    ids = [item.id for item in rows]
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile).filter(
            VehicleServiceTemplateProfile.template_item_id.in_(ids or [-1])
        ).all()
    }
    parts_map = _serialize_service_required_parts(db, ids)
    return [_service_item_to_response(row, profile_map.get(row.id), parts_map.get(row.id, [])) for row in rows]


@router.post("/vehicle-models/{model_id}/service-items", response_model=VehicleServiceTemplateItemResponse)
async def create_vehicle_service_item(
    model_id: int,
    payload: VehicleServiceTemplateItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")

    row = VehicleServiceTemplateItem(
        model_id=model_id,
        part_name=payload.service_name,
        part_code=payload.service_code,
        repair_method=payload.repair_method,
        labor_hours=payload.labor_hours,
        notes=payload.notes,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    profile = _ensure_service_profile(db, row.id)
    profile.labor_price = payload.labor_price
    profile.suggested_price = payload.suggested_price
    _upsert_service_required_parts(db, row.id, payload.required_parts)
    db.commit()
    db.refresh(row)
    db.refresh(profile)
    parts_map = _serialize_service_required_parts(db, [row.id])
    return _service_item_to_response(row, profile, parts_map.get(row.id, []))


@router.put("/vehicle-models/{model_id}/service-items/{item_id}", response_model=VehicleServiceTemplateItemResponse)
async def update_vehicle_service_item(
    model_id: int,
    item_id: int,
    payload: VehicleServiceTemplateItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleServiceTemplateItem)
        .filter(VehicleServiceTemplateItem.id == item_id, VehicleServiceTemplateItem.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Service item not found")

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "service_name" in patch:
        row.part_name = patch.pop("service_name")
    if "service_code" in patch:
        row.part_code = patch.pop("service_code")

    profile = _ensure_service_profile(db, row.id)
    if "labor_price" in patch:
        profile.labor_price = patch.pop("labor_price")
    if "suggested_price" in patch:
        profile.suggested_price = patch.pop("suggested_price")
    required_parts = patch.pop("required_parts", None)

    for key, value in patch.items():
        setattr(row, key, value)
    if required_parts is not None:
        _upsert_service_required_parts(db, row.id, required_parts)

    db.commit()
    db.refresh(row)
    db.refresh(profile)
    parts_map = _serialize_service_required_parts(db, [row.id])
    return _service_item_to_response(row, profile, parts_map.get(row.id, []))


@router.post("/vehicle-models/{model_id}/service-items/sync-manual-parts")
async def sync_vehicle_service_item_manual_parts(
    model_id: int,
    item_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    if item_id is not None:
        row = (
            db.query(VehicleServiceTemplateItem)
            .filter(VehicleServiceTemplateItem.id == item_id, VehicleServiceTemplateItem.model_id == model_id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Service item not found")
        item_ids = [item_id]
    else:
        item_ids = None

    results = _sync_service_item_required_parts_from_manual(db, model_id, service_item_ids=item_ids)
    db.commit()
    refreshed_ids = [item["service_item_id"] for item in results]
    parts_map = _serialize_service_required_parts(db, refreshed_ids)
    return {
        "model_id": model_id,
        "synced": len([item for item in results if item["updated"]]),
        "items": [
            {
                **item,
                "required_parts": parts_map.get(item["service_item_id"], item["required_parts"]),
            }
            for item in results
        ],
    }


@router.delete("/vehicle-models/{model_id}/service-items/{item_id}")
async def delete_vehicle_service_item(
    model_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleServiceTemplateItem)
        .filter(VehicleServiceTemplateItem.id == item_id, VehicleServiceTemplateItem.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Service item not found")
    db.query(VehicleServiceTemplatePart).filter(VehicleServiceTemplatePart.template_item_id == item_id).delete(synchronize_session=False)
    db.query(VehicleServiceTemplateProfile).filter(VehicleServiceTemplateProfile.template_item_id == item_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": item_id, "model_id": model_id}


@router.get("/vehicle-models/{model_id}/service-packages", response_model=list[VehicleServicePackageResponse])
async def list_vehicle_service_packages(
    model_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    _ensure_baseline_service_packages_for_model(db, model_id)
    db.commit()
    q = db.query(VehicleServicePackage).filter(VehicleServicePackage.model_id == model_id)
    if active_only:
        q = q.filter(VehicleServicePackage.is_active.is_(True))
    rows = q.order_by(VehicleServicePackage.sort_order.asc(), VehicleServicePackage.id.asc()).all()
    for row in rows:
        _recalculate_service_package_totals(db, row)
    db.commit()
    items_map = _serialize_service_package_items(db, [row.id for row in rows])
    return [_service_package_to_response(row, items_map.get(row.id, [])) for row in rows]


@router.post("/vehicle-models/{model_id}/service-packages/seed-defaults")
async def seed_vehicle_service_packages(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    created = _ensure_baseline_service_packages_for_model(db, model_id)
    db.commit()
    return {"model_id": model_id, "created": created}


@router.post("/vehicle-models/{model_id}/service-packages", response_model=VehicleServicePackageResponse)
async def create_vehicle_service_package(
    model_id: int,
    payload: VehicleServicePackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    row = VehicleServicePackage(
        model_id=model_id,
        package_code=payload.package_code,
        package_name=payload.package_name,
        description=payload.description,
        recommended_interval_km=payload.recommended_interval_km,
        recommended_interval_months=payload.recommended_interval_months,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    _upsert_service_package_items(db, row.id, payload.items)
    db.flush()
    _recalculate_service_package_totals(db, row)
    db.commit()
    db.refresh(row)
    items_map = _serialize_service_package_items(db, [row.id])
    return _service_package_to_response(row, items_map.get(row.id, []))


@router.put("/vehicle-models/{model_id}/service-packages/{package_id}", response_model=VehicleServicePackageResponse)
async def update_vehicle_service_package(
    model_id: int,
    package_id: int,
    payload: VehicleServicePackageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleServicePackage)
        .filter(VehicleServicePackage.id == package_id, VehicleServicePackage.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Service package not found")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    items = patch.pop("items", None)
    for key, value in patch.items():
        setattr(row, key, value)
    if items is not None:
        _upsert_service_package_items(db, row.id, items)
        db.flush()
    _recalculate_service_package_totals(db, row)
    db.commit()
    db.refresh(row)
    items_map = _serialize_service_package_items(db, [row.id])
    return _service_package_to_response(row, items_map.get(row.id, []))


@router.delete("/vehicle-models/{model_id}/service-packages/{package_id}")
async def delete_vehicle_service_package(
    model_id: int,
    package_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"])),
):
    row = (
        db.query(VehicleServicePackage)
        .filter(VehicleServicePackage.id == package_id, VehicleServicePackage.model_id == model_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Service package not found")
    db.query(VehicleServicePackageItem).filter(VehicleServicePackageItem.package_id == package_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": package_id, "model_id": model_id}


@router.get("/parts", response_model=dict)
async def list_parts(
    keyword: str = "",
    category: str = "",
    active_only: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    q = db.query(PartCatalogItem)
    if active_only:
        q = q.filter(PartCatalogItem.is_active.is_(True))
    if category:
        q = q.filter(PartCatalogItem.category == category)
    if keyword:
        q = q.filter(
            or_(
                PartCatalogItem.part_no.ilike(f"%{keyword}%"),
                PartCatalogItem.name.ilike(f"%{keyword}%"),
                PartCatalogItem.brand.ilike(f"%{keyword}%"),
            )
        )
    if keyword:
        candidates = q.all()
        ranked = sorted(
            candidates,
            key=lambda row: _rank_part(row, keyword),
            reverse=True,
        )
        total = len(ranked)
        rows = ranked[(page - 1) * size:(page - 1) * size + size]
    else:
        total = q.count()
        rows = q.order_by(PartCatalogItem.id.desc()).offset((page - 1) * size).limit(size).all()
    ids = [item.id for item in rows]
    profile_map = {
        row.part_id: row
        for row in db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id.in_(ids or [-1])).all()
    }
    items = [_part_to_response(row, profile_map.get(row.id)) for row in rows]
    return {"items": items, "page": page, "size": size, "total": total, "has_more": (page * size) < total}


@router.get("/parts/categories", response_model=list[str])
async def list_part_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper"])),
):
    _seed_default_catalog_if_needed(db)
    rows = (
        db.query(PartCatalogItem.category)
        .filter(PartCatalogItem.category.isnot(None))
        .filter(func.length(PartCatalogItem.category) > 0)
        .distinct()
        .order_by(PartCatalogItem.category.asc())
        .all()
    )
    return [row[0] for row in rows if row[0]]

@router.post("/parts", response_model=PartCatalogItemResponse)
async def create_part(
    payload: PartCatalogItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper"])),
):
    if db.query(PartCatalogItem.id).filter(PartCatalogItem.part_no == payload.part_no).first():
        raise HTTPException(status_code=400, detail="part_no already exists")

    row = PartCatalogItem(
        part_no=payload.part_no,
        name=payload.name,
        brand=payload.brand,
        category=payload.category,
        unit=payload.unit,
        compatible_model_ids=payload.compatible_model_ids,
        min_stock=payload.min_stock,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    profile = _ensure_part_profile(db, row.id)
    profile.sale_price = payload.sale_price
    profile.cost_price = payload.cost_price
    profile.stock_qty = payload.stock_qty
    profile.supplier_name = payload.supplier_name
    db.commit()
    db.refresh(row)
    db.refresh(profile)
    return _part_to_response(row, profile)


@router.put("/parts/{part_id}", response_model=PartCatalogItemResponse)
async def update_part(
    part_id: int,
    payload: PartCatalogItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper"])),
):
    row = db.query(PartCatalogItem).filter(PartCatalogItem.id == part_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Part not found")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "part_no" in patch:
        conflict = (
            db.query(PartCatalogItem.id)
            .filter(PartCatalogItem.part_no == patch["part_no"], PartCatalogItem.id != part_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="part_no already exists")

    profile = _ensure_part_profile(db, row.id)
    for key in ("sale_price", "cost_price", "stock_qty", "supplier_name"):
        if key in patch:
            setattr(profile, key, patch.pop(key))
    for key, value in patch.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    db.refresh(profile)
    return _part_to_response(row, profile)


@router.delete("/parts/{part_id}")
async def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper"])),
):
    row = db.query(PartCatalogItem).filter(PartCatalogItem.id == part_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Part not found")
    db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id == part_id).delete(synchronize_session=False)
    db.query(VehicleServiceTemplatePart).filter(VehicleServiceTemplatePart.part_id == part_id).update({"part_id": None}, synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"deleted": 1, "id": part_id}


@router.post("/parts/batch-delete")
async def batch_delete_parts(
    payload: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper"])),
):
    if not payload.ids:
        return {"requested": 0, "deleted": 0}

    db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id.in_(payload.ids)).delete(synchronize_session=False)
    db.query(VehicleServiceTemplatePart).filter(VehicleServiceTemplatePart.part_id.in_(payload.ids)).update({"part_id": None}, synchronize_session=False)
    deleted = db.query(PartCatalogItem).filter(PartCatalogItem.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"requested": len(payload.ids), "deleted": int(deleted)}
