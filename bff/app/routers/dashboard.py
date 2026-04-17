from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from ..core.db import get_db
from ..core.security import require_roles
from ..schemas.auth import User
from ..models import WorkOrder, PaymentLedger, Quote, WorkOrderAdvancedProfile, WorkOrderDeliveryChecklist, VehicleHealthRecord
from ..core.store import resolve_store_id

router = APIRouter(prefix="/mp/dashboard", tags=["Dashboard"])


def _utc_day_range():
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@router.get("/summary", response_model=dict)
async def dashboard_summary(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "cashier"]))
):
    store_id = resolve_store_id(request, current_user)

    total_orders = db.query(func.count(WorkOrder.id)).filter(WorkOrder.store_id == store_id).scalar() or 0
    active_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id, WorkOrder.status.notin_(["done", "cancel"]))
        .scalar()
        or 0
    )
    done_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id, WorkOrder.status == "done")
        .scalar()
        or 0
    )

    pending_payments = (
        db.query(func.count(PaymentLedger.id))
        .filter(PaymentLedger.store_id == store_id, PaymentLedger.status == "pending")
        .scalar()
        or 0
    )
    paid_amount_total = (
        db.query(func.coalesce(func.sum(PaymentLedger.amount), 0))
        .filter(PaymentLedger.store_id == store_id, PaymentLedger.status == "success")
        .scalar()
        or 0
    )

    active_quotes = (
        db.query(func.count(Quote.id))
        .filter(Quote.store_id == store_id, Quote.is_active == True)
        .scalar()
        or 0
    )

    status_distribution = (
        db.query(WorkOrder.status, func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id)
        .group_by(WorkOrder.status)
        .all()
    )
    status_counts = {status or "unknown": count for status, count in status_distribution}

    return {
        "orders": {
            "total": int(total_orders),
            "active": int(active_orders),
            "done": int(done_orders),
            "status_counts": status_counts,
        },
        "payments": {
            "pending_count": int(pending_payments),
            "paid_amount_total": float(paid_amount_total),
        },
        "quotes": {
            "active_count": int(active_quotes),
        },
    }


@router.get("/overview", response_model=dict)
async def dashboard_overview(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "cashier", "staff"])),
):
    store_id = resolve_store_id(request, current_user)
    day_start, day_end = _utc_day_range()

    total_orders = db.query(func.count(WorkOrder.id)).filter(WorkOrder.store_id == store_id).scalar() or 0
    active_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id, WorkOrder.status.notin_(["done", "cancel"]))
        .scalar()
        or 0
    )
    done_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id, WorkOrder.status == "done")
        .scalar()
        or 0
    )
    pending_payments = (
        db.query(func.count(PaymentLedger.id))
        .filter(PaymentLedger.store_id == store_id, PaymentLedger.status == "pending")
        .scalar()
        or 0
    )
    paid_amount_total = (
        db.query(func.coalesce(func.sum(PaymentLedger.amount), 0))
        .filter(PaymentLedger.store_id == store_id, PaymentLedger.status == "success")
        .scalar()
        or 0
    )
    active_quotes = (
        db.query(func.count(Quote.id))
        .filter(Quote.store_id == store_id, Quote.is_active == True)
        .scalar()
        or 0
    )
    today_new_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id, WorkOrder.created_at >= day_start, WorkOrder.created_at < day_end)
        .scalar()
        or 0
    )
    today_done_orders = (
        db.query(func.count(WorkOrder.id))
        .filter(
            WorkOrder.store_id == store_id,
            WorkOrder.status == "done",
            WorkOrder.created_at >= day_start,
            WorkOrder.created_at < day_end,
        )
        .scalar()
        or 0
    )
    today_paid_amount = (
        db.query(func.coalesce(func.sum(PaymentLedger.amount), 0))
        .filter(
            PaymentLedger.store_id == store_id,
            PaymentLedger.status == "success",
            PaymentLedger.created_at >= day_start,
            PaymentLedger.created_at < day_end,
        )
        .scalar()
        or 0
    )
    overdue_active_count = (
        db.query(func.count(WorkOrder.id))
        .filter(
            WorkOrder.store_id == store_id,
            WorkOrder.status.notin_(["done", "cancel"]),
            WorkOrder.created_at < (datetime.now(timezone.utc) - timedelta(hours=48)),
        )
        .scalar()
        or 0
    )
    urgent_orders_count = (
        db.query(func.count(WorkOrderAdvancedProfile.id))
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrderAdvancedProfile.is_urgent.is_(True),
        )
        .scalar()
        or 0
    )
    rework_orders_count = (
        db.query(func.count(WorkOrderAdvancedProfile.id))
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrderAdvancedProfile.is_rework.is_(True),
        )
        .scalar()
        or 0
    )
    quote_pending_confirmation_count = (
        db.query(func.count(Quote.id))
        .filter(Quote.store_id == store_id, Quote.is_active.is_(True), Quote.status == "published")
        .scalar()
        or 0
    )
    assigned_in_progress_count = (
        db.query(func.count(WorkOrderAdvancedProfile.id))
        .join(
            WorkOrder,
            (WorkOrder.uuid == WorkOrderAdvancedProfile.work_order_uuid)
            & (WorkOrder.store_id == WorkOrderAdvancedProfile.store_id),
        )
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrder.status.in_(["quoted", "in_progress", "ready"]),
            WorkOrderAdvancedProfile.assigned_technician.isnot(None),
            WorkOrderAdvancedProfile.assigned_technician != "",
        )
        .scalar()
        or 0
    )
    service_bay_active_count = (
        db.query(func.count(func.distinct(WorkOrderAdvancedProfile.service_bay)))
        .join(
            WorkOrder,
            (WorkOrder.uuid == WorkOrderAdvancedProfile.work_order_uuid)
            & (WorkOrder.store_id == WorkOrderAdvancedProfile.store_id),
        )
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrder.status.in_(["quoted", "in_progress", "ready"]),
            WorkOrderAdvancedProfile.service_bay.isnot(None),
            WorkOrderAdvancedProfile.service_bay != "",
        )
        .scalar()
        or 0
    )
    promised_due_soon_count = (
        db.query(func.count(WorkOrderAdvancedProfile.id))
        .join(
            WorkOrder,
            (WorkOrder.uuid == WorkOrderAdvancedProfile.work_order_uuid)
            & (WorkOrder.store_id == WorkOrderAdvancedProfile.store_id),
        )
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrder.status.in_(["quoted", "in_progress", "ready"]),
            WorkOrderAdvancedProfile.promised_at.isnot(None),
            WorkOrderAdvancedProfile.promised_at >= datetime.now(timezone.utc),
            WorkOrderAdvancedProfile.promised_at < (datetime.now(timezone.utc) + timedelta(hours=6)),
        )
        .scalar()
        or 0
    )
    missing_health_check_count = (
        db.query(func.count(WorkOrder.id))
        .outerjoin(
            WorkOrderDeliveryChecklist,
            (WorkOrderDeliveryChecklist.work_order_uuid == WorkOrder.uuid)
            & (WorkOrderDeliveryChecklist.store_id == WorkOrder.store_id),
        )
        .filter(
            WorkOrder.store_id == store_id,
            WorkOrder.status.in_(["in_progress", "ready"]),
            ~db.query(VehicleHealthRecord.id)
            .filter(
                VehicleHealthRecord.store_id == store_id,
                VehicleHealthRecord.customer_id == WorkOrder.customer_id,
                VehicleHealthRecord.vehicle_plate == WorkOrder.vehicle_plate,
            )
            .exists(),
        )
        .scalar()
        or 0
    )
    avg_ticket_amount = (
        db.query(func.coalesce(func.avg(PaymentLedger.amount), 0))
        .filter(PaymentLedger.store_id == store_id, PaymentLedger.status == "success")
        .scalar()
        or 0
    )
    status_distribution = (
        db.query(WorkOrder.status, func.count(WorkOrder.id))
        .filter(WorkOrder.store_id == store_id)
        .group_by(WorkOrder.status)
        .all()
    )
    status_counts = {status or "unknown": int(count) for status, count in status_distribution}
    delivery_ready_count = int(status_counts.get("ready", 0))

    recent_orders_rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.store_id == store_id)
        .order_by(WorkOrder.created_at.desc())
        .limit(10)
        .all()
    )
    recent_order_ids = [row.uuid for row in recent_orders_rows]
    advanced_profiles = (
        db.query(WorkOrderAdvancedProfile)
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrderAdvancedProfile.work_order_uuid.in_(recent_order_ids or ["-"]),
        )
        .all()
    )
    advanced_map = {row.work_order_uuid: row for row in advanced_profiles}
    recent_orders = [{
        "id": row.uuid,
        "status": row.status,
        "vehicle_plate": row.vehicle_plate,
        "customer_id": row.customer_id,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_urgent": bool(advanced_map.get(row.uuid).is_urgent) if advanced_map.get(row.uuid) else False,
        "is_rework": bool(advanced_map.get(row.uuid).is_rework) if advanced_map.get(row.uuid) else False,
        "assigned_technician": advanced_map.get(row.uuid).assigned_technician if advanced_map.get(row.uuid) else None,
    } for row in recent_orders_rows]

    recent_payments_rows = (
        db.query(PaymentLedger)
        .filter(PaymentLedger.store_id == store_id)
        .order_by(PaymentLedger.created_at.desc())
        .limit(10)
        .all()
    )
    recent_payments = [{
        "transaction_id": row.transaction_id,
        "work_order_id": row.work_order_id,
        "amount": float(row.amount or 0),
        "status": row.status,
        "provider": row.provider,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in recent_payments_rows]

    recent_quotes_rows = (
        db.query(Quote)
        .filter(Quote.store_id == store_id)
        .order_by(Quote.created_at.desc())
        .limit(10)
        .all()
    )
    recent_quotes = [{
        "work_order_id": row.work_order_uuid,
        "version": row.version,
        "amount_total": float(row.amount_total or 0),
        "status": row.status,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in recent_quotes_rows]

    technician_rows = (
        db.query(
            WorkOrderAdvancedProfile.assigned_technician,
            func.count(WorkOrderAdvancedProfile.id),
        )
        .join(
            WorkOrder,
            (WorkOrder.uuid == WorkOrderAdvancedProfile.work_order_uuid)
            & (WorkOrder.store_id == WorkOrderAdvancedProfile.store_id),
        )
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrder.status.in_(["quoted", "in_progress", "ready"]),
            WorkOrderAdvancedProfile.assigned_technician.isnot(None),
            WorkOrderAdvancedProfile.assigned_technician != "",
        )
        .group_by(WorkOrderAdvancedProfile.assigned_technician)
        .order_by(func.count(WorkOrderAdvancedProfile.id).desc(), WorkOrderAdvancedProfile.assigned_technician.asc())
        .limit(8)
        .all()
    )
    bay_rows = (
        db.query(
            WorkOrderAdvancedProfile.service_bay,
            func.count(WorkOrderAdvancedProfile.id),
        )
        .join(
            WorkOrder,
            (WorkOrder.uuid == WorkOrderAdvancedProfile.work_order_uuid)
            & (WorkOrder.store_id == WorkOrderAdvancedProfile.store_id),
        )
        .filter(
            WorkOrderAdvancedProfile.store_id == store_id,
            WorkOrder.status.in_(["quoted", "in_progress", "ready"]),
            WorkOrderAdvancedProfile.service_bay.isnot(None),
            WorkOrderAdvancedProfile.service_bay != "",
        )
        .group_by(WorkOrderAdvancedProfile.service_bay)
        .order_by(func.count(WorkOrderAdvancedProfile.id).desc(), WorkOrderAdvancedProfile.service_bay.asc())
        .limit(8)
        .all()
    )

    return {
        "orders": {
            "total": int(total_orders),
            "active": int(active_orders),
            "done": int(done_orders),
            "status_counts": status_counts,
        },
        "payments": {
            "pending_count": int(pending_payments),
            "paid_amount_total": float(paid_amount_total),
        },
        "quotes": {
            "active_count": int(active_quotes),
        },
        "kpi": {
            "today_new_orders": int(today_new_orders),
            "today_done_orders": int(today_done_orders),
            "today_paid_amount": float(today_paid_amount),
            "overdue_active_count": int(overdue_active_count),
            "urgent_orders_count": int(urgent_orders_count),
            "rework_orders_count": int(rework_orders_count),
            "quote_pending_confirmation_count": int(quote_pending_confirmation_count),
            "delivery_ready_count": int(delivery_ready_count),
            "assigned_in_progress_count": int(assigned_in_progress_count),
            "service_bay_active_count": int(service_bay_active_count),
            "promised_due_soon_count": int(promised_due_soon_count),
            "missing_health_check_count": int(missing_health_check_count),
            "avg_ticket_amount": float(avg_ticket_amount),
        },
        "recent": {
            "orders": recent_orders,
            "payments": recent_payments,
            "quotes": recent_quotes,
        },
        "operations": {
            "technicians": [
                {"name": name, "active_count": int(count)}
                for name, count in technician_rows
            ],
            "service_bays": [
                {"name": name, "active_count": int(count)}
                for name, count in bay_rows
            ],
        },
    }
