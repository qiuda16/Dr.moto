from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.db import get_db
from ..core.security import create_access_token
from ..core.text import compact_whitespace, normalize_text
from ..integrations.odoo import odoo_client
from ..models import (
    CustomerAppointmentDraft,
    CustomerAuthSession,
    CustomerSubscriptionPref,
    CustomerWechatBinding,
    PartCatalogItem,
    PartCatalogProfile,
    VehicleCatalogModel,
    VehicleHealthRecord,
    VehicleKnowledgeDocument,
    VehicleServicePackage,
    VehicleServicePackageItem,
    VehicleServiceTemplateItem,
    VehicleServiceTemplatePart,
    VehicleServiceTemplateProfile,
    WorkOrder,
    WorkOrderOfflinePayment,
    Quote,
)
from ..schemas.customer import CustomerVehicleCreate
from ..schemas.mp_customer import (
    CustomerBindRequest,
    CustomerBindResponse,
    CustomerAppointmentDraftCreate,
    CustomerAppointmentDraftResponse,
    CustomerHomeSummaryResponse,
    CustomerMaintenanceListResponse,
    CustomerProfileResponse,
    CustomerRefreshRequest,
    CustomerRefreshResponse,
    CustomerShopProductDetailResponse,
    CustomerShopProductListResponse,
    CustomerSubscriptionPrefUpsert,
    CustomerVehicleResponse,
    CustomerWechatLoginRequest,
    CustomerWechatLoginResponse,
)
from ..schemas.vehicle_health import VehicleHealthRecordCreate

router = APIRouter(prefix="/mp/customer", tags=["MP Customer"])
logger = logging.getLogger("bff")
redis_client = redis.Redis.from_url(settings.REDIS_URL)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = "".join(ch for ch in phone if ch.isdigit())
    if len(cleaned) < 7:
        return cleaned
    return f"{cleaned[:3]}****{cleaned[-4:]}"


def _safe_vehicle_plate(plate: str | None) -> str:
    normalized = compact_whitespace(plate) or ""
    return normalized.upper()


def _fetch_wechat_session(code: str) -> dict[str, str]:
    app_id = settings.WECHAT_APP_ID
    app_secret = settings.WECHAT_APP_SECRET
    if app_id and app_secret:
        try:
            resp = requests.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": app_id,
                    "secret": app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
                timeout=8,
            )
            payload = resp.json()
            openid = normalize_text(payload.get("openid"))
            if openid:
                return {
                    "openid": openid,
                    "unionid": normalize_text(payload.get("unionid")) or "",
                }
            errcode = payload.get("errcode")
            errmsg = payload.get("errmsg")
            logger.warning("wechat jscode2session invalid payload: %s", payload)
            if settings.is_production:
                raise HTTPException(status_code=502, detail=f"wechat login failed: {errcode or 'unknown'} {errmsg or ''}".strip())
        except Exception as exc:
            logger.warning("wechat jscode2session failed: %s", exc)
            if settings.is_production:
                raise HTTPException(status_code=502, detail="wechat login service unavailable")

    if settings.is_production:
        raise HTTPException(status_code=500, detail="wechat app credentials not configured")

    digest = hashlib.md5(code.encode("utf-8")).hexdigest()
    return {
        "openid": f"mock_openid_{digest[:16]}",
        "unionid": f"mock_unionid_{digest[16:32]}",
    }


def _find_catalog_model_id(db: Session, make: str | None, model: str | None, year: int | None) -> int | None:
    if not make or not model or not year:
        return None
    row = (
        db.query(VehicleCatalogModel.id)
        .filter(
            func.lower(VehicleCatalogModel.brand) == make.lower(),
            func.lower(VehicleCatalogModel.model_name) == model.lower(),
            VehicleCatalogModel.year_from <= year,
            func.coalesce(VehicleCatalogModel.year_to, year) >= year,
            VehicleCatalogModel.is_active.is_(True),
        )
        .first()
    )
    return int(row[0]) if row else None


def _load_customer_vehicles(partner_id: int, db: Session) -> list[dict[str, Any]]:
    vehicles = odoo_client.execute_kw(
        "drmoto.partner.vehicle",
        "search_read",
        [[["partner_id", "=", partner_id]]],
        {"fields": ["id", "license_plate", "vin", "vehicle_id"], "order": "id desc"},
    )
    model_ids = []
    for row in vehicles:
        ref = row.get("vehicle_id")
        if isinstance(ref, list) and ref:
            model_ids.append(ref[0])
    model_ids = list(dict.fromkeys(model_ids))
    model_map = {}
    if model_ids:
        model_rows = odoo_client.execute_kw(
            "drmoto.vehicle",
            "read",
            [model_ids, ["id", "make", "model", "year_from", "engine_code"]],
        )
        model_map = {m["id"]: m for m in model_rows}

    result = []
    for row in vehicles:
        ref = row.get("vehicle_id")
        model_id = ref[0] if isinstance(ref, list) and ref else None
        model = model_map.get(model_id, {})
        make = normalize_text(model.get("make"))
        model_name = normalize_text(model.get("model"))
        year = model.get("year_from") if isinstance(model.get("year_from"), int) else None
        result.append(
            {
                "id": int(row["id"]),
                "license_plate": _safe_vehicle_plate(row.get("license_plate")),
                "vin": normalize_text(row.get("vin") or None),
                "make": make,
                "model": model_name,
                "year": year,
                "engine_code": normalize_text(model.get("engine_code") or None),
                "catalog_model_id": _find_catalog_model_id(db, make, model_name, year),
            }
        )
    return result


def _build_vehicle_key(vehicle: dict[str, Any]) -> str:
    return "|".join(
        [
            normalize_text(vehicle.get("make")) or "",
            normalize_text(vehicle.get("model")) or "",
            str(vehicle.get("year") or ""),
            normalize_text(vehicle.get("engine_code")) or "-",
        ]
    ).upper()


def _ensure_vehicle_model(db: Session, vehicle: dict[str, Any]) -> int:
    vehicle_key = _build_vehicle_key(vehicle)
    rows = odoo_client.execute_kw("drmoto.vehicle", "search_read", [[["key", "=", vehicle_key]]], {"fields": ["id"], "limit": 1})
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


def _create_customer_vehicle(db: Session, partner_id: int, vehicle: CustomerVehicleCreate) -> dict[str, Any]:
    resolved = {
        "license_plate": compact_whitespace(vehicle.license_plate),
        "make": compact_whitespace(vehicle.make),
        "model": compact_whitespace(vehicle.model),
        "year": vehicle.year,
        "engine_code": normalize_text(vehicle.engine_code),
        "vin": normalize_text(vehicle.vin),
        "color": normalize_text(vehicle.color),
    }
    vehicle_model_id = _ensure_vehicle_model(
        db,
        {
            "make": resolved["make"],
            "model": resolved["model"],
            "year": resolved["year"],
            "engine_code": resolved["engine_code"],
        },
    )
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
    catalog_model_id = _find_catalog_model_id(
        db,
        normalize_text(vehicle_model.get("make")),
        normalize_text(vehicle_model.get("model")),
        vehicle_model.get("year_from") if isinstance(vehicle_model.get("year_from"), int) else None,
    )
    return {
        "id": result["id"],
        "license_plate": _safe_vehicle_plate(result.get("license_plate")),
        "vin": normalize_text(result.get("vin") or None),
        "make": normalize_text(vehicle_model.get("make")),
        "model": normalize_text(vehicle_model.get("model")),
        "year": vehicle_model.get("year_from") if isinstance(vehicle_model.get("year_from"), int) else None,
        "engine_code": normalize_text(vehicle_model.get("engine_code") or None),
        "catalog_model_id": catalog_model_id,
    }


def _to_health_response(row: VehicleHealthRecord, prev: VehicleHealthRecord | None = None) -> dict[str, Any]:
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
        "created_at": row.created_at,
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


def _apply_customer_quote(db: Session, store_id: str, row: dict, work_order_uuid: str | None) -> None:
    if not work_order_uuid:
        return
    quote = db.query(Quote).filter(
        Quote.store_id == store_id,
        Quote.work_order_uuid == work_order_uuid,
        Quote.is_active.is_(True),
        Quote.status.in_(["published", "confirmed"]),
    ).order_by(Quote.version.desc()).first()
    if not quote:
        return
    row["amount_total"] = float(quote.amount_total)
    row["quote_summary"] = {"version": quote.version, "status": quote.status,
                            "amount_total": float(quote.amount_total)}
    if "lines" in row:
        row["lines"] = [{"name": item.get("name"), "quantity": item.get("qty", 1),
                         "price_unit": item.get("unit_price", 0),
                         "price_subtotal": round(item.get("qty", 1) * item.get("unit_price", 0), 2)}
                        for item in (quote.items_json or [])]


def _payment_summary_for_work_order_uuid(db: Session, store_id: str, work_order_uuid: str | None) -> dict[str, Any]:
    if not work_order_uuid:
        return {"status": "unpaid", "paid_amount": 0.0, "payment_method": None, "paid_at": None}
    rows = (
        db.query(WorkOrderOfflinePayment)
        .filter(
            WorkOrderOfflinePayment.store_id == store_id,
            WorkOrderOfflinePayment.work_order_uuid == work_order_uuid,
            WorkOrderOfflinePayment.status == "paid",
        )
        .order_by(WorkOrderOfflinePayment.received_at.desc(), WorkOrderOfflinePayment.id.desc())
        .all()
    )
    if not rows:
        return {"status": "unpaid", "paid_amount": 0.0, "payment_method": None, "paid_at": None}
    total = sum(float(row.amount or 0) for row in rows)
    latest = rows[0]
    return {
        "status": "paid",
        "paid_amount": total,
        "payment_method": latest.payment_method,
        "paid_at": latest.received_at,
    }


def _issue_customer_session(
    db: Session,
    binding: CustomerWechatBinding,
    customer_name: str,
    phone_masked: str | None,
    request: Request | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=30)
    sid = uuid.uuid4().hex
    refresh_plain = uuid.uuid4().hex
    token_payload = {
        "sub": str(binding.partner_id),
        "role": "customer",
        "store_id": binding.store_id,
        "customer_name": customer_name,
        "phone_masked": phone_masked,
        "sid": sid,
    }
    access_token = create_access_token(data=token_payload, expires_delta=access_expires)
    row = CustomerAuthSession(
        store_id=binding.store_id,
        partner_id=binding.partner_id,
        binding_id=binding.id,
        session_token_hash=_token_hash(access_token),
        refresh_token_hash=_token_hash(refresh_plain),
        expires_at=now + refresh_expires,
        device_type="wechat_mini_program",
        ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(row)
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_plain,
        "expires_in": int(access_expires.total_seconds()),
    }


def _decode_customer_context(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    auth_error = HTTPException(status_code=401, detail="Could not validate customer token")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        role = (payload.get("role") or "").lower()
        if role != "customer":
            raise auth_error
        partner_id = int(payload.get("sub"))
        sid = normalize_text(payload.get("sid"))
        if not sid:
            raise auth_error
    except (ValueError, TypeError, JWTError):
        raise auth_error

    session_hash = _token_hash(token)
    now = datetime.now(timezone.utc)
    session_row = (
        db.query(CustomerAuthSession)
        .filter(
            CustomerAuthSession.partner_id == partner_id,
            CustomerAuthSession.session_token_hash == session_hash,
            CustomerAuthSession.revoked_at.is_(None),
            CustomerAuthSession.expires_at > now,
        )
        .order_by(CustomerAuthSession.id.desc())
        .first()
    )
    if not session_row:
        raise auth_error

    return {
        "partner_id": partner_id,
        "store_id": payload.get("store_id") or settings.DEFAULT_STORE_ID,
        "customer_name": payload.get("customer_name") or "车主用户",
        "phone_masked": payload.get("phone_masked"),
        "session_id": session_row.id,
        "token": token,
    }


@router.post(
    "/auth/wechat-login",
    response_model=CustomerWechatLoginResponse,
    summary="微信登录",
    description="通过微信登录 code 获取绑定状态；未绑定返回 bind_ticket，已绑定直接返回 access_token。",
)
async def customer_wechat_login(
    payload: CustomerWechatLoginRequest,
    db: Session = Depends(get_db),
):
    code = compact_whitespace(payload.code)
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    wx = _fetch_wechat_session(code)
    openid = wx["openid"]
    unionid = wx["unionid"] or None
    store_id = compact_whitespace(payload.store_id) or settings.DEFAULT_STORE_ID

    binding = (
        db.query(CustomerWechatBinding)
        .filter(
            CustomerWechatBinding.store_id == store_id,
            CustomerWechatBinding.openid == openid,
            CustomerWechatBinding.status == "active",
        )
        .order_by(CustomerWechatBinding.id.desc())
        .first()
    )
    if binding:
        partner_rows = odoo_client.execute_kw(
            "res.partner",
            "search_read",
            [[["id", "=", binding.partner_id]]],
            {"fields": ["id", "name", "phone"], "limit": 1},
        )
        if partner_rows:
            partner = partner_rows[0]
            customer_name = normalize_text(partner.get("name")) or "车主用户"
            phone_masked = _mask_phone(normalize_text(partner.get("phone")))
            session_tokens = _issue_customer_session(db, binding, customer_name, phone_masked, None)
            return {
                "bound": True,
                "bind_ticket": None,
                "access_token": session_tokens["access_token"],
                "refresh_token": session_tokens["refresh_token"],
                "expires_in": session_tokens["expires_in"],
                "partner_id": int(binding.partner_id),
                "customer_name": customer_name,
                "phone_masked": phone_masked,
            }

    bind_ticket = uuid.uuid4().hex
    ticket = {
        "store_id": store_id,
        "openid": openid,
        "unionid": unionid,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.setex(f"mp:bind:{bind_ticket}", 600, json.dumps(ticket, ensure_ascii=True))
    return {
        "bound": False,
        "bind_ticket": bind_ticket,
        "access_token": None,
        "refresh_token": None,
        "expires_in": None,
        "partner_id": None,
        "customer_name": None,
        "phone_masked": None,
    }


@router.post(
    "/auth/bind",
    response_model=CustomerBindResponse,
    summary="绑定客户",
    description="使用 bind_ticket + 手机号 + 车牌完成客户绑定并签发会话 token。",
)
async def customer_bind(
    payload: CustomerBindRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ticket_key = f"mp:bind:{compact_whitespace(payload.bind_ticket)}"
    ticket_raw = redis_client.get(ticket_key)
    if not ticket_raw:
        raise HTTPException(status_code=400, detail="bind_ticket expired")
    redis_client.delete(ticket_key)
    try:
        ticket = json.loads(ticket_raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid bind_ticket")

    store_id = compact_whitespace(ticket.get("store_id")) or settings.DEFAULT_STORE_ID
    openid = compact_whitespace(ticket.get("openid"))
    unionid = compact_whitespace(ticket.get("unionid"))
    if not openid:
        raise HTTPException(status_code=400, detail="openid missing in bind_ticket")

    phone = compact_whitespace(payload.phone)
    plate_no = _safe_vehicle_plate(payload.plate_no)
    if not phone or not plate_no:
        raise HTTPException(status_code=400, detail="phone and plate_no are required")

    partners = odoo_client.execute_kw(
        "res.partner",
        "search_read",
        [[["phone", "=", phone]]],
        {"fields": ["id", "name", "phone"], "limit": 1},
    )
    if not partners:
        raise HTTPException(status_code=404, detail="customer not found by phone")
    partner = partners[0]
    partner_id = int(partner["id"])

    vehicles = odoo_client.execute_kw(
        "drmoto.partner.vehicle",
        "search_read",
        [[["partner_id", "=", partner_id], ["license_plate", "=", plate_no]]],
        {"fields": ["id"], "limit": 1},
    )
    if not vehicles:
        raise HTTPException(status_code=403, detail="plate not matched with customer")

    existing_by_openid = (
        db.query(CustomerWechatBinding)
        .filter(CustomerWechatBinding.store_id == store_id, CustomerWechatBinding.openid == openid)
        .order_by(CustomerWechatBinding.id.desc())
        .first()
    )
    if existing_by_openid and existing_by_openid.partner_id != partner_id and existing_by_openid.status == "active":
        raise HTTPException(status_code=409, detail="openid already bound to another customer")

    binding = existing_by_openid
    if not binding:
        binding = CustomerWechatBinding(
            store_id=store_id,
            partner_id=partner_id,
            openid=openid,
            unionid=unionid,
            phone=phone,
            status="active",
        )
        db.add(binding)
        db.flush()
    else:
        binding.partner_id = partner_id
        binding.unionid = unionid
        binding.phone = phone
        binding.status = "active"
        binding.unbound_at = None
        binding.updated_at = datetime.now(timezone.utc)
        db.flush()

    customer_name = normalize_text(partner.get("name")) or "车主用户"
    phone_masked = _mask_phone(normalize_text(partner.get("phone")))
    session_tokens = _issue_customer_session(db, binding, customer_name, phone_masked, request)
    return {
        "bound": True,
        "access_token": session_tokens["access_token"],
        "refresh_token": session_tokens["refresh_token"],
        "expires_in": session_tokens["expires_in"],
        "partner_id": partner_id,
        "customer_name": customer_name,
        "phone_masked": phone_masked,
    }


@router.post(
    "/auth/refresh",
    response_model=CustomerRefreshResponse,
    summary="刷新令牌",
    description="使用 refresh_token 刷新 access_token。",
)
async def customer_refresh_token(
    payload: CustomerRefreshRequest,
    db: Session = Depends(get_db),
):
    refresh_token = compact_whitespace(payload.refresh_token)
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    now = datetime.now(timezone.utc)
    row = (
        db.query(CustomerAuthSession)
        .filter(
            CustomerAuthSession.refresh_token_hash == _token_hash(refresh_token),
            CustomerAuthSession.revoked_at.is_(None),
            CustomerAuthSession.expires_at > now,
        )
        .order_by(CustomerAuthSession.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=401, detail="invalid refresh_token")

    binding = db.query(CustomerWechatBinding).filter(CustomerWechatBinding.id == row.binding_id).first()
    if not binding or binding.status != "active":
        raise HTTPException(status_code=401, detail="binding inactive")

    partners = odoo_client.execute_kw(
        "res.partner",
        "search_read",
        [[["id", "=", row.partner_id]]],
        {"fields": ["id", "name", "phone"], "limit": 1},
    )
    customer_name = "车主用户"
    phone_masked = None
    if partners:
        customer_name = normalize_text(partners[0].get("name")) or customer_name
        phone_masked = _mask_phone(normalize_text(partners[0].get("phone")))

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "sub": str(row.partner_id),
        "role": "customer",
        "store_id": row.store_id,
        "customer_name": customer_name,
        "phone_masked": phone_masked,
        "sid": uuid.uuid4().hex,
    }
    access_token = create_access_token(token_payload, access_expires)
    row.session_token_hash = _token_hash(access_token)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": access_token, "expires_in": int(access_expires.total_seconds())}


@router.post(
    "/auth/logout",
    summary="退出登录",
    description="注销当前 access_token 对应的会话。",
)
async def customer_logout(
    ctx: dict = Depends(_decode_customer_context),
    db: Session = Depends(get_db),
):
    session_hash = _token_hash(ctx["token"])
    row = (
        db.query(CustomerAuthSession)
        .filter(CustomerAuthSession.id == ctx["session_id"], CustomerAuthSession.session_token_hash == session_hash)
        .first()
    )
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"success": True}


@router.get(
    "/me",
    response_model=CustomerProfileResponse,
    summary="当前车主信息",
)
async def customer_me(ctx: dict = Depends(_decode_customer_context)):
    return {
        "partner_id": ctx["partner_id"],
        "customer_name": ctx["customer_name"],
        "phone_masked": ctx["phone_masked"],
        "store_id": ctx["store_id"],
    }


@router.get(
    "/vehicles",
    response_model=list[CustomerVehicleResponse],
    summary="车辆列表",
    description="返回当前车主可访问的车辆列表。",
)
async def customer_vehicles(
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    return _load_customer_vehicles(ctx["partner_id"], db)


@router.post(
    "/vehicles",
    response_model=CustomerVehicleResponse,
    summary="新增车辆",
)
async def customer_vehicle_create(
    payload: CustomerVehicleCreate,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    try:
        return _create_customer_vehicle(db, ctx["partner_id"], payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("customer vehicle create failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create customer vehicle")


@router.delete(
    "/vehicles/{vehicle_id}",
    summary="删除车辆",
)
async def customer_vehicle_delete(
    vehicle_id: int,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    try:
        rows = odoo_client.execute_kw(
            "drmoto.partner.vehicle",
            "search_read",
            [[["id", "=", vehicle_id], ["partner_id", "=", ctx["partner_id"]]]],
            {"fields": ["id"], "limit": 1},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Vehicle record not found")
        odoo_client.execute_kw("drmoto.partner.vehicle", "unlink", [[vehicle_id]])
        return {"deleted": 1, "vehicle_id": vehicle_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("customer vehicle delete failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete customer vehicle")


@router.get(
    "/home",
    response_model=CustomerHomeSummaryResponse,
    summary="首页摘要",
)
async def customer_home(
    vehicle_id: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None) if vehicle_id else (vehicles[0] if vehicles else None)
    if not target:
        return {
            "latest_odometer_km": None,
            "health_records_count": 0,
            "pending_recommendations": 0,
            "latest_order_status": None,
            "latest_measured_at": None,
        }

    plate = target["license_plate"]
    q = db.query(VehicleHealthRecord).filter(
        VehicleHealthRecord.store_id == ctx["store_id"],
        VehicleHealthRecord.customer_id == str(ctx["partner_id"]),
        VehicleHealthRecord.vehicle_plate == plate,
    )
    latest = q.order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc()).first()
    health_count = q.count()

    pending_recommendations = 0
    if target.get("catalog_model_id"):
        pending_recommendations = (
            db.query(VehicleServiceTemplateItem)
            .filter(
                VehicleServiceTemplateItem.model_id == target["catalog_model_id"],
                VehicleServiceTemplateItem.is_active.is_(True),
            )
            .count()
        )

    latest_order_status = None
    try:
        domain = [["customer_id", "=", ctx["partner_id"]], ["vehicle_plate", "=", plate]]
        rows = odoo_client.execute_kw(
            "drmoto.work.order",
            "search_read",
            [domain],
            {"fields": ["state"], "limit": 1, "order": "create_date desc"},
        )
        if rows:
            latest_order_status = normalize_text(rows[0].get("state"))
    except Exception as exc:
        logger.warning("customer home latest order query failed: %s", exc)

    return {
        "latest_odometer_km": float(latest.odometer_km) if latest else None,
        "health_records_count": int(health_count),
        "pending_recommendations": int(pending_recommendations),
        "latest_order_status": latest_order_status,
        "latest_measured_at": latest.measured_at if latest else None,
    }


@router.get(
    "/vehicles/{vehicle_id}/health-records",
    summary="体检记录",
)
async def customer_vehicle_health_records(
    vehicle_id: int,
    limit: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="vehicle not found")

    rows = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == ctx["store_id"],
            VehicleHealthRecord.customer_id == str(ctx["partner_id"]),
            VehicleHealthRecord.vehicle_plate == target["license_plate"],
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "customer_id": row.customer_id,
            "vehicle_plate": row.vehicle_plate,
            "measured_at": row.measured_at,
            "created_at": row.created_at,
            "odometer_km": float(row.odometer_km),
            "engine_rpm": row.engine_rpm,
            "battery_voltage": row.battery_voltage,
            "tire_front_psi": row.tire_front_psi,
            "tire_rear_psi": row.tire_rear_psi,
            "coolant_temp_c": row.coolant_temp_c,
            "oil_life_percent": row.oil_life_percent,
            "notes": row.notes,
            "extra": row.extra_json,
        }
        for row in rows
    ]


@router.post(
    "/vehicles/{vehicle_id}/health-records",
    summary="新增体检记录",
)
async def customer_vehicle_health_records_create(
    vehicle_id: int,
    payload: VehicleHealthRecordCreate,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="vehicle not found")

    measured_at = payload.measured_at or datetime.now(timezone.utc)
    row = VehicleHealthRecord(
        store_id=ctx["store_id"],
        customer_id=str(ctx["partner_id"]),
        vehicle_plate=target["license_plate"],
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
        created_by=f"customer:{ctx['partner_id']}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    prev = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == ctx["store_id"],
            VehicleHealthRecord.customer_id == str(ctx["partner_id"]),
            VehicleHealthRecord.vehicle_plate == target["license_plate"],
            VehicleHealthRecord.id != row.id,
            VehicleHealthRecord.measured_at <= row.measured_at,
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    return _to_health_response(row, prev)


@router.get(
    "/vehicles/{vehicle_id}/maintenance-orders",
    response_model=CustomerMaintenanceListResponse,
    summary="保养记录列表",
)
async def customer_vehicle_maintenance_orders(
    vehicle_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="vehicle not found")

    offset = (page - 1) * size
    domain = [["customer_id", "=", ctx["partner_id"]], ["vehicle_plate", "=", target["license_plate"]]]
    fields = ["id", "name", "vehicle_plate", "state", "date_planned", "amount_total", "create_date", "bff_uuid"]
    total = odoo_client.execute_kw("drmoto.work.order", "search_count", [domain])
    items = odoo_client.execute_kw(
        "drmoto.work.order",
        "search_read",
        [domain],
        {"fields": fields, "limit": size, "offset": offset, "order": "create_date desc"},
    )
    for item in items:
        _apply_customer_quote(db, ctx["store_id"], item, normalize_text(item.get("bff_uuid")))
        item["payment_summary"] = _payment_summary_for_work_order_uuid(db, ctx["store_id"], normalize_text(item.get("bff_uuid")))
    return {"page": page, "size": size, "total": int(total or 0), "items": items}


@router.get(
    "/maintenance-orders/{order_id}",
    summary="保养记录详情",
)
async def customer_maintenance_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    rows = odoo_client.execute_kw(
        "drmoto.work.order",
        "search_read",
        [[["id", "=", order_id], ["customer_id", "=", ctx["partner_id"]]]],
        {"fields": ["id", "name", "vehicle_plate", "state", "date_planned", "amount_total", "description", "bff_uuid"], "limit": 1},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="order not found")
    row = rows[0]
    line_rows = odoo_client.execute_kw(
        "drmoto.work.order.line",
        "search_read",
        [[["order_id", "=", order_id]]],
        {"fields": ["id", "name", "quantity", "price_unit", "price_subtotal", "product_id"]},
    )
    row["lines"] = line_rows
    bff_uuid = normalize_text(row.get("bff_uuid"))
    if not bff_uuid:
        local = db.query(WorkOrder).filter(WorkOrder.store_id == ctx["store_id"], WorkOrder.odoo_id == order_id).first()
        bff_uuid = local.uuid if local else None
    row["payment_summary"] = _payment_summary_for_work_order_uuid(db, ctx["store_id"], bff_uuid)
    _apply_customer_quote(db, ctx["store_id"], row, bff_uuid)
    return row


@router.get(
    "/vehicles/{vehicle_id}/recommended-services",
    summary="推荐保养项目",
)
async def customer_vehicle_recommended_services(
    vehicle_id: int,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="vehicle not found")
    model_id = target.get("catalog_model_id")
    if not model_id:
        return []

    template_rows = (
        db.query(VehicleServiceTemplateItem)
        .filter(
            VehicleServiceTemplateItem.model_id == model_id,
            VehicleServiceTemplateItem.is_active.is_(True),
        )
        .order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc())
        .limit(100)
        .all()
    )
    ids = [row.id for row in template_rows]
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile).filter(VehicleServiceTemplateProfile.template_item_id.in_(ids or [-1])).all()
    }
    part_rows = (
        db.query(VehicleServiceTemplatePart)
        .filter(VehicleServiceTemplatePart.template_item_id.in_(ids or [-1]))
        .order_by(VehicleServiceTemplatePart.sort_order.asc(), VehicleServiceTemplatePart.id.asc())
        .all()
    )
    parts_map: dict[int, list[dict[str, Any]]] = {}
    for part in part_rows:
        parts_map.setdefault(part.template_item_id, []).append(
            {
                "part_no": part.part_no,
                "part_name": part.part_name,
                "qty": float(part.qty),
                "unit_price": part.unit_price,
                "is_optional": bool(part.is_optional),
            }
        )

    return [
        {
            "template_item_id": row.id,
            "service_code": row.part_code,
            "service_name": row.part_name,
            "repair_method": row.repair_method,
            "suggested_price": profile_map.get(row.id).suggested_price if profile_map.get(row.id) else None,
            "labor_price": profile_map.get(row.id).labor_price if profile_map.get(row.id) else None,
            "required_parts": parts_map.get(row.id, []),
            "level": "suggest",
            "reason": "基于车型模板推荐，后续可叠加里程与体检规则。",
        }
        for row in template_rows
    ]


@router.get(
    "/vehicles/{vehicle_id}/knowledge-docs",
    summary="保养科普资料",
)
async def customer_vehicle_knowledge_docs(
    vehicle_id: int,
    category: str = Query(""),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    target = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="vehicle not found")
    model_id = target.get("catalog_model_id")
    if not model_id:
        return []

    q = db.query(VehicleKnowledgeDocument).filter(VehicleKnowledgeDocument.model_id == model_id)
    normalized_category = normalize_text(category)
    if normalized_category:
        q = q.filter(VehicleKnowledgeDocument.category == normalized_category)
    rows = q.order_by(VehicleKnowledgeDocument.created_at.desc(), VehicleKnowledgeDocument.id.desc()).limit(100).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "file_name": row.file_name,
            "file_url": row.file_url,
            "file_type": row.file_type,
            "category": row.category,
            "notes": row.notes,
        }
        for row in rows
    ]


@router.get(
    "/subscriptions",
    summary="订阅偏好列表",
)
async def customer_subscription_list(
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    rows = (
        db.query(CustomerSubscriptionPref)
        .filter(
            CustomerSubscriptionPref.store_id == ctx["store_id"],
            CustomerSubscriptionPref.partner_id == ctx["partner_id"],
        )
        .order_by(CustomerSubscriptionPref.vehicle_id.asc().nullsfirst(), CustomerSubscriptionPref.id.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "vehicle_id": row.vehicle_id,
            "notify_enabled": bool(row.notify_enabled),
            "remind_before_days": int(row.remind_before_days),
            "remind_before_km": int(row.remind_before_km),
            "prefer_channel": row.prefer_channel,
            "last_notified_at": row.last_notified_at,
        }
        for row in rows
    ]


@router.put(
    "/subscriptions",
    summary="更新订阅偏好",
)
async def customer_subscription_upsert(
    payload: CustomerSubscriptionPrefUpsert,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    if payload.remind_before_days < 0 or payload.remind_before_km < 0:
        raise HTTPException(status_code=400, detail="remind values must be >= 0")

    row = (
        db.query(CustomerSubscriptionPref)
        .filter(
            CustomerSubscriptionPref.store_id == ctx["store_id"],
            CustomerSubscriptionPref.partner_id == ctx["partner_id"],
            and_(
                CustomerSubscriptionPref.vehicle_id == payload.vehicle_id
                if payload.vehicle_id is not None
                else CustomerSubscriptionPref.vehicle_id.is_(None)
            ),
        )
        .first()
    )
    if row is None:
        row = CustomerSubscriptionPref(
            store_id=ctx["store_id"],
            partner_id=ctx["partner_id"],
            vehicle_id=payload.vehicle_id,
        )
        db.add(row)
    row.notify_enabled = payload.notify_enabled
    row.remind_before_days = payload.remind_before_days
    row.remind_before_km = payload.remind_before_km
    row.prefer_channel = payload.prefer_channel
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "vehicle_id": row.vehicle_id,
        "notify_enabled": bool(row.notify_enabled),
        "remind_before_days": int(row.remind_before_days),
        "remind_before_km": int(row.remind_before_km),
        "prefer_channel": row.prefer_channel,
        "last_notified_at": row.last_notified_at,
    }


def _resolve_vehicle_for_customer(vehicle_id: int | None, db: Session, ctx: dict[str, Any]) -> dict[str, Any] | None:
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    if not vehicles:
        return None
    if vehicle_id:
        return next((item for item in vehicles if item["id"] == vehicle_id), None)
    return vehicles[0]


def _build_inspection_items(latest: VehicleHealthRecord | None) -> list[dict[str, Any]]:
    metrics = [
        ("engine_rpm", "发动机转速", getattr(latest, "engine_rpm", None), "rpm"),
        ("battery_voltage", "电瓶电压", getattr(latest, "battery_voltage", None), "V"),
        ("tire_front_psi", "前胎压", getattr(latest, "tire_front_psi", None), "psi"),
        ("tire_rear_psi", "后胎压", getattr(latest, "tire_rear_psi", None), "psi"),
        ("coolant_temp_c", "冷却液温度", getattr(latest, "coolant_temp_c", None), "°C"),
        ("oil_life_percent", "机油寿命", getattr(latest, "oil_life_percent", None), "%"),
        ("lighting", "灯光", "正常", ""),
        ("chain_belt", "链条 / 皮带", "待检查", ""),
    ]
    items = []
    for key, label, value, unit in metrics:
        status = "unknown"
        advice = "建议到店确认"
        if value is not None and value != "":
            status = "normal"
            advice = "当前项目正常"
            if key == "battery_voltage" and float(value) < 12:
                status = "warning"
                advice = "电压偏低，建议尽快检查"
            if key.startswith("tire_") and float(value) < 26:
                status = "notice"
                advice = "胎压偏低，建议补压"
            if key == "coolant_temp_c" and float(value) > 105:
                status = "warning"
                advice = "温度偏高，建议尽快处理"
            if key == "oil_life_percent" and float(value) < 20:
                status = "notice"
                advice = "机油寿命偏低，建议安排保养"
        items.append(
            {
                "key": key,
                "label": label,
                "value": f"{value}{unit}" if value not in (None, "") and unit else (value if value not in (None, "") else "-"),
                "status": status,
                "advice": advice,
            }
        )
    return items


def _determine_health_state(items: list[dict[str, Any]]) -> str:
    statuses = [item.get("status") for item in items]
    if "warning" in statuses:
        return "warning"
    if "notice" in statuses:
        return "notice"
    if "normal" in statuses:
        return "normal"
    return "unknown"


def _build_health_summary(target: dict[str, Any], db: Session, ctx: dict[str, Any]) -> tuple[dict[str, Any], VehicleHealthRecord | None]:
    latest = (
        db.query(VehicleHealthRecord)
        .filter(
            VehicleHealthRecord.store_id == ctx["store_id"],
            VehicleHealthRecord.customer_id == str(ctx["partner_id"]),
            VehicleHealthRecord.vehicle_plate == target["license_plate"],
        )
        .order_by(VehicleHealthRecord.measured_at.desc(), VehicleHealthRecord.id.desc())
        .first()
    )
    inspection_items = _build_inspection_items(latest)
    pending_recommendations = 0
    if target.get("catalog_model_id"):
        pending_recommendations = (
            db.query(VehicleServiceTemplateItem)
            .filter(
                VehicleServiceTemplateItem.model_id == target["catalog_model_id"],
                VehicleServiceTemplateItem.is_active.is_(True),
            )
            .count()
        )
    flags = [item for item in inspection_items if item["status"] in {"warning", "notice"}][:3]
    return (
        {
            "latest_odometer_km": float(latest.odometer_km) if latest else None,
            "health_records_count": 1 if latest else 0,
            "pending_recommendations": int(pending_recommendations),
            "latest_order_status": "done",
            "latest_measured_at": latest.measured_at if latest else None,
            "flags": flags,
            "inspection_items": inspection_items,
        },
        latest,
    )


def _build_recommended_services(model_id: int | None, db: Session) -> list[dict[str, Any]]:
    if not model_id:
        return []
    template_rows = (
        db.query(VehicleServiceTemplateItem)
        .filter(
            VehicleServiceTemplateItem.model_id == model_id,
            VehicleServiceTemplateItem.is_active.is_(True),
        )
        .order_by(VehicleServiceTemplateItem.sort_order.asc(), VehicleServiceTemplateItem.id.asc())
        .limit(20)
        .all()
    )
    ids = [row.id for row in template_rows]
    profile_map = {
        row.template_item_id: row
        for row in db.query(VehicleServiceTemplateProfile).filter(VehicleServiceTemplateProfile.template_item_id.in_(ids or [-1])).all()
    }
    return [
        {
            "id": row.id,
            "service_name": row.part_name,
            "service_code": row.part_code,
            "repair_method": row.repair_method,
            "suggested_price": profile_map.get(row.id).suggested_price if profile_map.get(row.id) else None,
        }
        for row in template_rows
    ]


def _build_shop_items(model_id: int | None, db: Session) -> list[dict[str, Any]]:
    if not model_id:
        return []
    items: list[dict[str, Any]] = []
    package_rows = (
        db.query(VehicleServicePackage)
        .filter(VehicleServicePackage.model_id == model_id, VehicleServicePackage.is_active.is_(True))
        .order_by(VehicleServicePackage.sort_order.asc(), VehicleServicePackage.id.asc())
        .limit(10)
        .all()
    )
    for row in package_rows:
        items.append(
            {
                "product_type": "package",
                "id": row.id,
                "name": row.package_name,
                "category": "套餐",
                "description": row.description,
                "price": row.suggested_price_total,
                "stock_qty": None,
                "is_recommended": True,
                "compatible_model_ids": [model_id],
                "payload": {
                    "recommended_interval_km": row.recommended_interval_km,
                    "recommended_interval_months": row.recommended_interval_months,
                },
            }
        )
    service_rows = _build_recommended_services(model_id, db)
    for row in service_rows:
        items.append(
            {
                "product_type": "service",
                "id": row["id"],
                "name": row["service_name"],
                "category": "服务",
                "description": row["repair_method"],
                "price": row["suggested_price"],
                "stock_qty": None,
                "is_recommended": True,
                "compatible_model_ids": [model_id],
                "payload": {},
            }
        )
    part_rows = (
        db.query(PartCatalogItem, PartCatalogProfile)
        .outerjoin(PartCatalogProfile, PartCatalogProfile.part_id == PartCatalogItem.id)
        .filter(PartCatalogItem.is_active.is_(True))
        .limit(20)
        .all()
    )
    for part, profile in part_rows:
        compatible = part.compatible_model_ids or []
        if compatible and model_id not in compatible:
            continue
        items.append(
            {
                "product_type": "part",
                "id": part.id,
                "name": part.name,
                "category": part.category,
                "description": part.brand,
                "price": profile.sale_price if profile else None,
                "stock_qty": profile.stock_qty if profile else None,
                "is_recommended": True,
                "compatible_model_ids": compatible or [model_id],
                "payload": {
                    "unit": part.unit,
                    "brand": part.brand,
                },
            }
        )
    return items


@router.get("/cockpit", summary="客户驾驶舱")
async def customer_cockpit(
    vehicle_id: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    target = _resolve_vehicle_for_customer(vehicle_id, db, ctx)
    vehicles = _load_customer_vehicles(ctx["partner_id"], db)
    if not target:
        return {
            "selected_vehicle_id": None,
            "vehicle": None,
            "vehicles": vehicles,
            "health_state": "unknown",
            "health_summary": {"inspection_items": []},
            "recommended_services": [],
            "knowledge_docs": [],
            "shop_items": [],
        }
    health_summary, _latest = _build_health_summary(target, db, ctx)
    knowledge_docs = await customer_vehicle_knowledge_docs(target["id"], "", db, ctx)
    recommended_services = _build_recommended_services(target.get("catalog_model_id"), db)
    shop_items = _build_shop_items(target.get("catalog_model_id"), db)[:6]
    return {
        "selected_vehicle_id": target["id"],
        "vehicle": target,
        "vehicles": vehicles,
        "health_state": _determine_health_state(health_summary["inspection_items"]),
        "health_summary": health_summary,
        "recommended_services": recommended_services,
        "knowledge_docs": knowledge_docs,
        "shop_items": shop_items,
    }


@router.get("/shop/products", response_model=CustomerShopProductListResponse, summary="商城商品列表")
async def customer_shop_products(
    vehicle_id: int | None = Query(None),
    kind: str = Query(""),
    query: str = Query(""),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    target = _resolve_vehicle_for_customer(vehicle_id, db, ctx)
    items = _build_shop_items(target.get("catalog_model_id") if target else None, db)
    normalized_kind = normalize_text(kind)
    normalized_query = normalize_text(query)
    if normalized_kind:
        items = [item for item in items if item["product_type"] == normalized_kind]
    if normalized_query:
        items = [item for item in items if normalized_query in normalize_text(item["name"]).lower() or normalized_query in normalize_text(item.get("description")).lower()]
    return {"items": items}


@router.get("/shop/recommendations", response_model=CustomerShopProductListResponse, summary="商城推荐")
async def customer_shop_recommendations(
    vehicle_id: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    target = _resolve_vehicle_for_customer(vehicle_id, db, ctx)
    return {"items": _build_shop_items(target.get("catalog_model_id") if target else None, db)[:6]}


@router.get("/shop/products/{product_id}", response_model=CustomerShopProductDetailResponse, summary="商品详情")
async def customer_shop_product_detail(
    product_id: int,
    product_type: str = Query("part"),
    vehicle_id: int | None = Query(None),
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    target = _resolve_vehicle_for_customer(vehicle_id, db, ctx)
    items = _build_shop_items(target.get("catalog_model_id") if target else None, db)
    item = next((row for row in items if row["id"] == product_id and row["product_type"] == normalize_text(product_type)), None)
    if not item:
        raise HTTPException(status_code=404, detail="product not found")
    return {"item": item}


@router.post("/appointments/draft", response_model=CustomerAppointmentDraftResponse, summary="创建预约草稿")
async def customer_create_appointment_draft(
    payload: CustomerAppointmentDraftCreate,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    target = _resolve_vehicle_for_customer(payload.vehicle_id, db, ctx) if payload.vehicle_id else _resolve_vehicle_for_customer(None, db, ctx)
    draft = CustomerAppointmentDraft(
        store_id=ctx["store_id"],
        partner_id=ctx["partner_id"],
        vehicle_id=target["id"] if target else payload.vehicle_id,
        vehicle_plate=target["license_plate"] if target else None,
        subject=compact_whitespace(payload.subject) or "预约草稿",
        service_kind=normalize_text(payload.service_kind),
        source=normalize_text(payload.source) or "mini_program",
        preferred_date=payload.preferred_date,
        notes=compact_whitespace(payload.notes),
        payload=payload.payload or {},
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/appointments/draft/{draft_id}", response_model=CustomerAppointmentDraftResponse, summary="预约草稿详情")
async def customer_get_appointment_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    ctx: dict = Depends(_decode_customer_context),
):
    draft = (
        db.query(CustomerAppointmentDraft)
        .filter(
            CustomerAppointmentDraft.id == draft_id,
            CustomerAppointmentDraft.partner_id == ctx["partner_id"],
            CustomerAppointmentDraft.store_id == ctx["store_id"],
        )
        .first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail="draft not found")
    return draft
