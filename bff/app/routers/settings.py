from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import get_current_user, require_roles
from ..core.store import resolve_store_id
from ..models import AppSetting
from ..schemas.auth import User
from ..schemas.settings import AppSettingsResponse, AppSettingsUpdate

router = APIRouter(prefix="/mp/settings", tags=["Settings"])

DEFAULT_COMPLAINT_PHRASES = [
    "常规保养，检查机油与机滤",
    "更换机油机滤，检查链条状态",
    "前刹车异响，顺便做安全检查",
    "检查电瓶状态与充电系统",
]


def _default_settings_payload(store_id: str) -> dict:
    return {
        "store_id": store_id,
        "store_name": "机车博士",
        "brand_name": "DrMoto",
        "sidebar_badge_text": "门店管理",
        "primary_color": "#409EFF",
        "default_labor_price": 80.0,
        "default_delivery_note": "已向客户说明施工内容，建议按期复检。",
        "document_header_note": "摩托车售后服务专业单据",
        "customer_document_footer_note": "请客户核对维修项目、金额与交车说明后签字确认。",
        "internal_document_footer_note": "用于门店内部留档、责任追溯与施工复核。",
        "default_service_advice": "建议客户按保养周期复检，并关注油液、制动与轮胎状态。",
        "common_complaint_phrases_json": list(DEFAULT_COMPLAINT_PHRASES),
        "updated_by": None,
    }


def _get_or_create_settings(db: Session, store_id: str) -> AppSetting:
    row = (
        db.query(AppSetting)
        .filter(AppSetting.store_id == store_id)
        .order_by(AppSetting.id.desc())
        .first()
    )
    if row:
        return row

    row = AppSetting(**_default_settings_payload(store_id))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _to_response(row: AppSetting) -> AppSettingsResponse:
    return AppSettingsResponse(
        store_id=row.store_id,
        store_name=row.store_name,
        brand_name=row.brand_name,
        sidebar_badge_text=row.sidebar_badge_text,
        primary_color=row.primary_color,
        default_labor_price=row.default_labor_price,
        default_delivery_note=row.default_delivery_note,
        document_header_note=row.document_header_note,
        customer_document_footer_note=row.customer_document_footer_note,
        internal_document_footer_note=row.internal_document_footer_note,
        default_service_advice=row.default_service_advice,
        common_complaint_phrases=list(row.common_complaint_phrases_json or []),
        updated_by=row.updated_by,
    )


@router.get("", response_model=AppSettingsResponse)
async def get_app_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    store_id = resolve_store_id(request, current_user)
    row = _get_or_create_settings(db, store_id)
    return _to_response(row)


@router.put("", response_model=AppSettingsResponse, dependencies=[Depends(require_roles(["admin"]))])
async def update_app_settings(
    payload: AppSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store_id = resolve_store_id(request, current_user)
    row = _get_or_create_settings(db, store_id)

    row.store_name = payload.store_name
    row.brand_name = payload.brand_name
    row.sidebar_badge_text = payload.sidebar_badge_text
    row.primary_color = payload.primary_color
    row.default_labor_price = payload.default_labor_price
    row.default_delivery_note = payload.default_delivery_note
    row.document_header_note = payload.document_header_note
    row.customer_document_footer_note = payload.customer_document_footer_note
    row.internal_document_footer_note = payload.internal_document_footer_note
    row.default_service_advice = payload.default_service_advice
    row.common_complaint_phrases_json = payload.common_complaint_phrases
    row.updated_by = current_user.username

    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)
