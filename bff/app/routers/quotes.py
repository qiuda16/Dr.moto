from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import require_roles
from ..schemas.auth import User
from ..schemas.quote import QuoteVersionCreate, QuoteVersionResponse
from ..models import Quote, WorkOrder
from ..core.audit import log_audit
from ..core.store import resolve_store_id

router = APIRouter(prefix="/mp/quotes", tags=["Quotes"])


def _quote_to_response(work_order_id: str, quote: Quote) -> QuoteVersionResponse:
    return QuoteVersionResponse(
        work_order_id=work_order_id,
        version=quote.version,
        status=quote.status,
        is_active=quote.is_active,
        amount_total=quote.amount_total,
        items=quote.items_json or [],
    )


@router.get("/{work_order_id}", response_model=list[QuoteVersionResponse])
async def list_quote_versions(
    work_order_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"]))
):
    store_id = resolve_store_id(request, current_user)
    quotes = (
        db.query(Quote)
        .filter(Quote.work_order_uuid == work_order_id, Quote.store_id == store_id)
        .order_by(Quote.version.desc())
        .all()
    )
    return [_quote_to_response(work_order_id, q) for q in quotes]


@router.post("/{work_order_id}/versions", response_model=QuoteVersionResponse)
async def create_quote_version(
    work_order_id: str,
    payload: QuoteVersionCreate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff"]))
):
    store_id = resolve_store_id(request, current_user)
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == work_order_id, WorkOrder.store_id == store_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Quote items cannot be empty")

    latest = (
        db.query(Quote)
        .filter(Quote.work_order_uuid == work_order_id, Quote.store_id == store_id)
        .order_by(Quote.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1
    amount_total = round(sum(item.qty * item.unit_price for item in payload.items), 2)

    quote = Quote(
        store_id=store_id,
        work_order_uuid=work_order_id,
        version=version,
        items_json=[item.model_dump() for item in payload.items],
        amount_total=amount_total,
        is_active=False,
        status="draft",
        created_by=current_user.username,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)

    log_audit(
        db,
        actor_id=current_user.username,
        action="create_quote_version",
        target=f"work_order:{work_order_id}",
        before=None,
        after={"version": version, "amount_total": amount_total, "status": "draft"},
        store_id=store_id,
    )
    return _quote_to_response(work_order_id, quote)


@router.post("/{work_order_id}/{version}/publish", response_model=QuoteVersionResponse)
async def publish_quote_version(
    work_order_id: str,
    version: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    store_id = resolve_store_id(request, current_user)
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == work_order_id, WorkOrder.store_id == store_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    quote = db.query(Quote).filter(
        Quote.work_order_uuid == work_order_id,
        Quote.version == version,
        Quote.store_id == store_id,
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote version not found")

    if quote.status not in {"draft", "published"}:
        raise HTTPException(status_code=409, detail=f"Quote version cannot be published from status={quote.status}")

    for q in db.query(Quote).filter(Quote.work_order_uuid == work_order_id, Quote.store_id == store_id).all():
        q.is_active = (q.version == version)
        if q.version == version:
            q.status = "published"

    wo.active_quote_version = version
    db.commit()
    db.refresh(quote)

    log_audit(
        db,
        actor_id=current_user.username,
        action="publish_quote_version",
        target=f"work_order:{work_order_id}",
        before=None,
        after={"active_quote_version": version},
        store_id=store_id,
    )
    return _quote_to_response(work_order_id, quote)


@router.post("/{work_order_id}/{version}/confirm", response_model=QuoteVersionResponse)
async def confirm_quote_version(
    work_order_id: str,
    version: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "cashier"]))
):
    store_id = resolve_store_id(request, current_user)
    quote = db.query(Quote).filter(
        Quote.work_order_uuid == work_order_id,
        Quote.version == version,
        Quote.store_id == store_id,
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote version not found")

    if quote.status != "published":
        raise HTTPException(status_code=409, detail=f"Quote confirm requires published status, current={quote.status}")

    quote.status = "confirmed"
    quote.is_active = True
    db.commit()
    db.refresh(quote)

    log_audit(
        db,
        actor_id=current_user.username,
        action="confirm_quote_version",
        target=f"work_order:{work_order_id}",
        before=None,
        after={"version": version, "status": "confirmed"},
        store_id=store_id,
    )
    return _quote_to_response(work_order_id, quote)


@router.post("/{work_order_id}/{version}/reject", response_model=QuoteVersionResponse)
async def reject_quote_version(
    work_order_id: str,
    version: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "cashier"]))
):
    store_id = resolve_store_id(request, current_user)
    quote = db.query(Quote).filter(
        Quote.work_order_uuid == work_order_id,
        Quote.version == version,
        Quote.store_id == store_id,
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote version not found")

    if quote.status not in {"draft", "published"}:
        raise HTTPException(status_code=409, detail=f"Quote reject not allowed from status={quote.status}")

    quote.status = "rejected"
    quote.is_active = False
    db.commit()
    db.refresh(quote)

    log_audit(
        db,
        actor_id=current_user.username,
        action="reject_quote_version",
        target=f"work_order:{work_order_id}",
        before=None,
        after={"version": version, "status": "rejected"},
        store_id=store_id,
    )
    return _quote_to_response(work_order_id, quote)
