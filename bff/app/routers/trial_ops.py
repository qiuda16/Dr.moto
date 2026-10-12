from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import require_roles
from ..core.store import resolve_store_id
from ..core.text import compact_whitespace, normalize_text
from ..integrations.odoo import odoo_client
from ..models import (
    CustomerAppointmentDraft,
    WebsiteLead,
    WorkOrder,
    WorkOrderDeliveryChecklist,
    WorkOrderOfflinePayment,
)
from ..schemas.auth import User
from ..schemas.trial_ops import (
    OfflinePaymentCreate,
    TrialInboxItem,
    TrialWorkOrderCreate,
    WebsiteLeadCreate,
    WebsiteLeadUpdate,
)

router = APIRouter(prefix="/mp", tags=["Single Store Trial"])
logger = logging.getLogger("bff")


def _lead_to_response(row: WebsiteLead) -> dict[str, Any]:
    return {
        "id": row.id,
        "store_id": row.store_id,
        "name": row.name,
        "contact": row.contact,
        "identity": row.identity,
        "message": row.message,
        "source_page": row.source_page,
        "status": row.status,
        "assigned_to": row.assigned_to,
        "handled_by": row.handled_by,
        "handled_at": row.handled_at,
        "converted_work_order_uuid": row.converted_work_order_uuid,
        "notes": row.notes,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
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
        return row
    row = WorkOrderDeliveryChecklist(store_id=store_id, work_order_uuid=work_order_uuid)
    db.add(row)
    db.flush()
    return row


def _load_work_order(db: Session, store_id: str, order_id: str) -> WorkOrder:
    row = db.query(WorkOrder).filter(WorkOrder.store_id == store_id, WorkOrder.uuid == order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="work order not found")
    return row


def _create_local_and_odoo_work_order(
    db: Session,
    store_id: str,
    customer_id: str,
    vehicle_plate: str,
    description: str,
    preferred_date: datetime | None = None,
) -> WorkOrder:
    normalized_customer_id = compact_whitespace(customer_id)
    normalized_plate = compact_whitespace(vehicle_plate)
    normalized_description = compact_whitespace(description)
    if not normalized_customer_id or not normalized_plate or not normalized_description:
        raise HTTPException(status_code=400, detail="customer_id, vehicle_plate and description are required")

    try:
        customer_id_int = int(normalized_customer_id)
        if customer_id_int <= 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="customer_id must be a positive integer") from exc

    work_order_uuid = str(uuid.uuid4())
    planned_values = {}
    if preferred_date:
        planned_utc = preferred_date.astimezone(timezone.utc) if preferred_date.tzinfo else preferred_date
        planned_values["date_planned"] = planned_utc.strftime("%Y-%m-%d %H:%M:%S")
    odoo_id = None
    try:
        odoo_id = odoo_client.execute_kw(
            "drmoto.work.order",
            "create",
            [
                {
                    "name": "New",
                    "customer_id": customer_id_int,
                    "vehicle_plate": normalized_plate,
                    "description": normalized_description,
                    "bff_uuid": work_order_uuid,
                    **planned_values,
                }
            ],
        )
    except Exception as exc:
        logger.error("trial work order odoo create failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create work order in Odoo") from exc

    row = WorkOrder(
        uuid=work_order_uuid,
        store_id=store_id,
        odoo_id=odoo_id,
        customer_id=normalized_customer_id,
        vehicle_plate=normalized_plate,
        description=normalized_description,
        status="draft",
    )
    db.add(row)
    db.flush()
    return row


@router.post("/leads", summary="官网线索提交")
async def create_website_lead(payload: WebsiteLeadCreate, request: Request, db: Session = Depends(get_db)):
    store_id = compact_whitespace(payload.store_id) or "default"
    source_page = payload.source_page or str(request.headers.get("referer") or "")
    row = WebsiteLead(
        store_id=store_id,
        name=payload.name,
        contact=payload.contact,
        identity=payload.identity or "rider",
        message=payload.message,
        source_page=source_page,
        status="new",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "lead": _lead_to_response(row)}


@router.get("/leads", summary="官网线索列表")
async def list_website_leads(
    status: str = Query("", max_length=40),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    q = db.query(WebsiteLead).filter(WebsiteLead.store_id == store_id)
    normalized_status = normalize_text(status)
    if normalized_status:
        q = q.filter(WebsiteLead.status == normalized_status)
    total = q.count()
    rows = q.order_by(WebsiteLead.created_at.desc(), WebsiteLead.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"items": [_lead_to_response(row) for row in rows], "page": page, "size": size, "total": total}


@router.put("/leads/{lead_id}", summary="更新官网线索状态")
async def update_website_lead(
    lead_id: int,
    payload: WebsiteLeadUpdate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    row = db.query(WebsiteLead).filter(WebsiteLead.store_id == store_id, WebsiteLead.id == lead_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="lead not found")
    patch = payload.model_dump(exclude_unset=True)
    if "status" in patch and patch["status"] is not None:
        row.status = normalize_text(patch["status"]) or row.status
        if row.status in {"contacted", "converted", "closed"}:
            row.handled_by = current_user.username
            row.handled_at = datetime.now(timezone.utc)
    if "assigned_to" in patch:
        row.assigned_to = normalize_text(patch["assigned_to"])
    if "notes" in patch:
        row.notes = compact_whitespace(patch["notes"])
    db.commit()
    db.refresh(row)
    return _lead_to_response(row)


@router.get("/trial/inbox", response_model=list[TrialInboxItem], summary="试运营待办池")
async def list_trial_inbox(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    leads = (
        db.query(WebsiteLead)
        .filter(WebsiteLead.store_id == store_id, WebsiteLead.status.in_(["new", "contacted"]))
        .order_by(WebsiteLead.created_at.desc(), WebsiteLead.id.desc())
        .limit(80)
        .all()
    )
    drafts = (
        db.query(CustomerAppointmentDraft)
        .filter(CustomerAppointmentDraft.store_id == store_id, CustomerAppointmentDraft.status.in_(["draft", "submitted"]))
        .order_by(CustomerAppointmentDraft.created_at.desc(), CustomerAppointmentDraft.id.desc())
        .limit(80)
        .all()
    )
    items: list[dict[str, Any]] = []
    for lead in leads:
        items.append(
            {
                "source_type": "lead",
                "id": lead.id,
                "status": lead.status,
                "title": lead.name,
                "contact": lead.contact,
                "identity": lead.identity,
                "message": lead.message,
                "source": lead.source_page,
                "created_at": lead.created_at,
                "converted_work_order_uuid": lead.converted_work_order_uuid,
                "payload": {"notes": lead.notes},
            }
        )
    for draft in drafts:
        items.append(
            {
                "source_type": "appointment",
                "id": draft.id,
                "status": draft.status,
                "title": draft.subject,
                "contact": str(draft.partner_id),
                "identity": "customer",
                "vehicle_plate": draft.vehicle_plate,
                "preferred_date": draft.preferred_date,
                "message": draft.notes,
                "source": draft.source,
                "created_at": draft.created_at,
                "payload": draft.payload or {},
            }
        )
    return sorted(items, key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


@router.post("/trial/workorders", summary="从线索或预约创建工单")
async def create_trial_work_order(
    payload: TrialWorkOrderCreate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    if payload.source_type == "appointment":
        draft = (
            db.query(CustomerAppointmentDraft)
            .filter(CustomerAppointmentDraft.store_id == store_id, CustomerAppointmentDraft.id == payload.source_id)
            .first()
        )
        if not draft:
            raise HTTPException(status_code=404, detail="appointment draft not found")
        if draft.status == "converted" or (draft.payload or {}).get("converted_work_order_uuid"):
            raise HTTPException(status_code=409, detail="appointment has already been converted")
        customer_id = payload.customer_id or str(draft.partner_id)
        vehicle_plate = payload.vehicle_plate or draft.vehicle_plate
        description = payload.description or "；".join([part for part in [draft.subject, draft.notes] if part])
        description = "\n".join([description, f"Source: {draft.source or 'mini_program'}; appointment #{draft.id}"])
        work_order = _create_local_and_odoo_work_order(
            db, store_id, customer_id, vehicle_plate or "", description, draft.preferred_date)
        draft.status = "converted"
        draft.payload = {**(draft.payload or {}), "converted_work_order_uuid": work_order.uuid}
    else:
        lead = db.query(WebsiteLead).filter(WebsiteLead.store_id == store_id, WebsiteLead.id == payload.source_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="lead not found")
        if lead.converted_work_order_uuid:
            raise HTTPException(status_code=409, detail="lead has already been converted")
        if not payload.customer_id or not payload.vehicle_plate:
            raise HTTPException(status_code=400, detail="customer_id and vehicle_plate are required for lead conversion")
        description = payload.description or "；".join([part for part in [lead.message, f"官网线索：{lead.name} {lead.contact}"] if part])
        work_order = _create_local_and_odoo_work_order(db, store_id, payload.customer_id, payload.vehicle_plate, description)
        lead.status = "converted"
        lead.converted_work_order_uuid = work_order.uuid
        lead.handled_by = current_user.username
        lead.handled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(work_order)
    return {
        "id": work_order.uuid,
        "status": work_order.status,
        "data": {
            "customer_id": work_order.customer_id,
            "vehicle_plate": work_order.vehicle_plate,
            "description": work_order.description,
            "odoo_id": work_order.odoo_id,
        },
    }


@router.post("/workorders/{order_id}/offline-payment", summary="记录线下收款")
async def record_offline_payment(
    order_id: str,
    payload: OfflinePaymentCreate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"])),
):
    store_id = resolve_store_id(request, current_user)
    work_order = _load_work_order(db, store_id, order_id)
    if payload.idempotency_key:
        existing = (
            db.query(WorkOrderOfflinePayment)
            .filter(
                WorkOrderOfflinePayment.store_id == store_id,
                WorkOrderOfflinePayment.idempotency_key == payload.idempotency_key,
            )
            .first()
        )
        if existing:
            if existing.work_order_uuid != work_order.uuid:
                raise HTTPException(status_code=409, detail="idempotency key already belongs to another work order")
            return {
                "id": existing.id,
                "work_order_id": existing.work_order_uuid,
                "amount": existing.amount,
                "payment_method": existing.payment_method,
                "status": existing.status,
                "received_by": existing.received_by,
                "received_at": existing.received_at,
            }
    payment = WorkOrderOfflinePayment(
        store_id=store_id,
        work_order_uuid=work_order.uuid,
        amount=float(payload.amount),
        payment_method=payload.payment_method,
        status="paid",
        payer_note=compact_whitespace(payload.payer_note),
        idempotency_key=compact_whitespace(payload.idempotency_key),
        received_by=current_user.username,
        received_at=payload.received_at or datetime.now(timezone.utc),
    )
    checklist = _ensure_delivery_checklist(db, store_id, work_order.uuid)
    checklist.payment_confirmed = True
    checklist.payment_method = payload.payment_method
    checklist.payment_amount = float(payload.amount)
    if payload.payer_note:
        checklist.notes = compact_whitespace(payload.payer_note)
    checklist.updated_by = current_user.username
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "work_order_id": work_order.uuid,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "status": payment.status,
        "received_by": payment.received_by,
        "received_at": payment.received_at,
    }


@router.get("/workorders/{order_id}/offline-payments", summary="线下收款记录")
async def list_offline_payments(
    order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier", "keeper"])),
):
    store_id = resolve_store_id(request, current_user)
    work_order = _load_work_order(db, store_id, order_id)
    rows = (
        db.query(WorkOrderOfflinePayment)
        .filter(WorkOrderOfflinePayment.store_id == store_id, WorkOrderOfflinePayment.work_order_uuid == work_order.uuid)
        .order_by(WorkOrderOfflinePayment.received_at.desc(), WorkOrderOfflinePayment.id.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "amount": row.amount,
            "payment_method": row.payment_method,
            "status": row.status,
            "payer_note": row.payer_note,
            "received_by": row.received_by,
            "received_at": row.received_at,
        }
        for row in rows
    ]
