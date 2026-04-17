from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

from ..core.config import settings
from ..core.db import get_db
from ..core.security import require_roles
from ..models import PaymentLedger, WorkOrder, PaymentEvent
from ..schemas.payment import PaymentCreate, PaymentIntentCreate, PaymentIntentResponse, PaymentCallback
from ..schemas.auth import User
from ..core.store import resolve_store_id
from ..integrations.payment_provider import build_payment_intent, verify_provider_webhook_signature, SUPPORTED_PROVIDERS
import redis

router = APIRouter(prefix="/mp/payments", tags=["Payments"])
logger = logging.getLogger("bff")
redis_client = redis.Redis.from_url(settings.REDIS_URL)

@router.post("/create_intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    intent: PaymentIntentCreate, 
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(["admin", "manager", "cashier", "staff"]))
):
    store_id = resolve_store_id(request, current_user)
    idem_key = None
    if request:
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            cached = redis_client.get(f"idempotency:intent:{store_id}:{idem_key}")
            if cached:
                return json.loads(cached.decode("utf-8"))

    # 1. Verify Work Order
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == intent.work_order_id, WorkOrder.store_id == store_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    provider = (intent.provider or settings.PAYMENT_PROVIDER).strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        
    # 2. Generate Transaction ID
    transaction_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    
    # 3. Create Ledger Entry (Pending)
    payment = PaymentLedger(
        transaction_id=transaction_id,
        store_id=store_id,
        work_order_id=intent.work_order_id,
        amount=intent.amount,
        status="pending",
        provider=provider
    )
    db.add(payment)
    db.commit()

    amount_fen = int((Decimal(str(intent.amount)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if amount_fen <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount after conversion to fen")
    
    try:
        intent_result = build_payment_intent(
            provider=provider,
            transaction_id=transaction_id,
            amount=float(intent.amount),
            amount_fen=amount_fen,
            work_order_id=intent.work_order_id,
            store_id=store_id,
            base_url="http://localhost:8080",
        )
    except Exception as e:
        logger.error(f"Payment intent build error: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    
    result = {
        "payment_id": transaction_id,
        "payment_url": intent_result.payment_url,
        "status": intent_result.status
    }
    if idem_key:
        redis_client.setex(
            f"idempotency:intent:{store_id}:{idem_key}",
            settings.IDEMPOTENCY_TTL_SECONDS,
            json.dumps(result),
        )
    return result

@router.get("/provider_redirect", response_class=HTMLResponse)
async def provider_redirect_page(provider: str, transaction_id: str, amount: float, store_id: str = "default"):
    normalized = (provider or "").strip().lower()
    if normalized == "wechat":
        # Integration skeleton page: in production, redirect to real provider URL.
        return f"""
        <html>
            <head><title>WeChat Pay Redirect</title></head>
            <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h2>WeChat Pay Redirect (Skeleton)</h2>
                <p>Transaction: <strong>{transaction_id}</strong></p>
                <p>Amount: <strong>{amount}</strong></p>
                <p>Store: <strong>{store_id}</strong></p>
                <p>This environment is using integration skeleton. Configure real WeChat API call to replace this page.</p>
            </body>
        </html>
        """
    raise HTTPException(status_code=400, detail="Unsupported provider redirect")


def _render_mock_gateway_page(id: str, amount: float, store_id: str) -> str:
    return f"""
    <html>
        <head>
            <title>DrMoto Mock Pay</title>
            <style>
                body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }}
                .card {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                button {{ background: #07c160; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; }}
                button:hover {{ background: #06ad56; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>DrMoto Payment Gateway</h2>
                <p>Transaction: <strong>{id}</strong></p>
                <p>Amount: <strong>${amount}</strong></p>
                <button onclick="confirmPay()">Confirm Payment</button>
                <p id="msg"></p>
            </div>
            <script>
                async function confirmPay() {{
                    const btn = document.querySelector('button');
                    btn.disabled = true;
                    btn.innerText = 'Processing...';
                    
                    try {{
                        const res = await fetch('/mp/payments/mock_confirm', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json', 'X-Store-Id': '{store_id}' }},
                            body: JSON.stringify({{ transaction_id: '{id}', store_id: '{store_id}' }})
                        }});
                        const data = await res.json();
                        if (data.status === 'success') {{
                            document.getElementById('msg').innerText = 'Payment Successful! You can close this window.';
                            document.getElementById('msg').style.color = 'green';
                        }} else {{
                            throw new Error(data.detail || 'Failed');
                        }}
                    }} catch (err) {{
                        document.getElementById('msg').innerText = err.message;
                        document.getElementById('msg').style.color = 'red';
                        btn.disabled = false;
                    }}
                }}
            </script>
        </body>
    </html>
    """


@router.get("/mock_gateway", response_class=HTMLResponse)
async def mock_gateway_page_with_store(id: str, amount: float, store_id: str = "default"):
    if not settings.ENABLE_MOCK_PAYMENT:
        raise HTTPException(status_code=404, detail="Mock payment endpoint disabled")
    return _render_mock_gateway_page(id=id, amount=amount, store_id=store_id)

@router.post("/mock_confirm")
async def confirm_mock_payment(
    payload: dict,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "manager"]))
):
    payload_store_id = (payload.get("store_id") or "").strip().lower()
    store_id = payload_store_id or resolve_store_id(request, current_user)
    if not settings.ENABLE_MOCK_PAYMENT:
        raise HTTPException(status_code=404, detail="Mock payment endpoint disabled")
    transaction_id = payload.get("transaction_id")
    payment = db.query(PaymentLedger).filter(
        PaymentLedger.transaction_id == transaction_id,
        PaymentLedger.store_id == store_id,
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    if payment.status == "success":
        return {"status": "success", "message": "Already paid"}
        
    payment.status = "success"
    db.commit()
    
    # Notify Odoo? Or assume Odoo pulls?
    # For now, we just update local ledger.
    # In a real app, we might call Odoo to register payment on the Repair Order.
    
    return {"status": "success"}


@router.post("/webhook/{provider}")
async def payment_webhook(
    provider: str,
    callback: PaymentCallback,
    request: Request,
    db: Session = Depends(get_db),
):
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    raw = await request.body()
    signature = request.headers.get("X-Payment-Signature")
    header_map = {k.lower(): v for k, v in request.headers.items()}
    signature_verified = verify_provider_webhook_signature(
        provider=normalized_provider,
        raw_body=raw,
        signature=signature,
        headers=header_map,
    )
    if not signature_verified:
        raise HTTPException(status_code=401, detail="Invalid payment signature")

    store_id = resolve_store_id(request, None)
    ledger = db.query(PaymentLedger).filter(
        PaymentLedger.transaction_id == callback.transaction_id,
        PaymentLedger.store_id == store_id,
    ).first()

    event = PaymentEvent(
        store_id=store_id,
        provider_ref=callback.provider_ref or callback.payment_id,
        raw_payload=raw.decode("utf-8", errors="replace"),
        signature_verified=True,
        processing_status="processed" if ledger else "ignored",
    )
    db.add(event)

    if not ledger:
        db.commit()
        return {"status": "ignored", "reason": "ledger_not_found"}

    status_text = (callback.status or "").strip().lower()
    if status_text in {"success", "paid", "completed"}:
        ledger.status = "success"
    elif status_text in {"failed", "cancelled", "canceled"}:
        ledger.status = "failed"
    else:
        ledger.status = "pending"

    db.commit()
    return {
        "status": "accepted",
        "transaction_id": callback.transaction_id,
        "ledger_status": ledger.status,
        "time": datetime.now(timezone.utc).isoformat(),
    }

@router.post("/record")
async def record_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(["admin", "manager", "cashier"]))
):
    store_id = resolve_store_id(request, current_user)
    # Legacy/Admin endpoint
    idem_key = None
    if request:
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            cached = redis_client.get(f"idempotency:{store_id}:{idem_key}")
            if cached:
                return json.loads(cached.decode("utf-8"))
                
    existing = db.query(PaymentLedger).filter(
        PaymentLedger.transaction_id == payment.transaction_id,
        PaymentLedger.store_id == store_id,
    ).first()
    if existing:
        if existing.status == "success":
            result = {"status": "recorded", "id": existing.id, "duplicate": True}
            if idem_key:
                redis_client.setex(
                    f"idempotency:{store_id}:{idem_key}",
                    settings.IDEMPOTENCY_TTL_SECONDS,
                    json.dumps(result),
                )
            return result
        raise HTTPException(status_code=409, detail="Transaction already exists with non-success status")

    db_payment = PaymentLedger(
        transaction_id=payment.transaction_id,
        store_id=store_id,
        work_order_id=payment.work_order_id,
        amount=payment.amount,
        status="success"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    result = {"status": "recorded", "id": db_payment.id}
    if idem_key:
        redis_client.setex(
            f"idempotency:{store_id}:{idem_key}",
            settings.IDEMPOTENCY_TTL_SECONDS,
            json.dumps(result),
        )
    return result
