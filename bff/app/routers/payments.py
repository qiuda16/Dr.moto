from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import json
import logging
import uuid
from datetime import datetime

from ..core.config import settings
from ..core.db import get_db
from ..core.security import get_current_user
from ..models import PaymentLedger, WorkOrder
from ..schemas.payment import PaymentCreate, PaymentIntentCreate, PaymentIntentResponse
import redis

router = APIRouter(prefix="/mp/payments", tags=["Payments"])
logger = logging.getLogger("bff")
redis_client = redis.Redis.from_url(settings.REDIS_URL)

@router.post("/create_intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    intent: PaymentIntentCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Verify Work Order
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == intent.work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    # 2. Generate Transaction ID
    transaction_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    
    # 3. Create Ledger Entry (Pending)
    payment = PaymentLedger(
        transaction_id=transaction_id,
        work_order_id=intent.work_order_id,
        amount=intent.amount,
        status="pending",
        provider=intent.provider
    )
    db.add(payment)
    db.commit()
    
    # 4. Generate Mock Payment URL
    # In real world, this would be WeChat/Stripe API call to get prepay_id/url
    payment_url = f"http://localhost:8080/mp/payments/mock_gateway?id={transaction_id}&amount={intent.amount}"
    
    return {
        "payment_id": transaction_id,
        "payment_url": payment_url,
        "status": "pending"
    }

@router.get("/mock_gateway", response_class=HTMLResponse)
async def mock_gateway_page(id: str, amount: float):
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
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ transaction_id: '{id}' }})
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

@router.post("/mock_confirm")
async def confirm_mock_payment(payload: dict, db: Session = Depends(get_db)):
    transaction_id = payload.get("transaction_id")
    payment = db.query(PaymentLedger).filter(PaymentLedger.transaction_id == transaction_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    if payment.status == "success":
        return {"status": "success", "message": "Already paid"}
        
    payment.status = "success"
    payment.updated_at = datetime.now()
    db.commit()
    
    # Notify Odoo? Or assume Odoo pulls?
    # For now, we just update local ledger.
    # In a real app, we might call Odoo to register payment on the Repair Order.
    
    return {"status": "success"}

@router.post("/record")
async def record_payment(payment: PaymentCreate, db: Session = Depends(get_db), request: Request = None):
    # Legacy/Admin endpoint
    idem_key = None
    if request:
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            cached = redis_client.get(f"idempotency:{idem_key}")
            if cached:
                return json.loads(cached.decode("utf-8"))
                
    db_payment = PaymentLedger(
        transaction_id=payment.transaction_id,
        work_order_id=payment.work_order_id,
        amount=payment.amount,
        status="success"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    result = {"status": "recorded", "id": db_payment.id}
    if idem_key:
        redis_client.setex(f"idempotency:{idem_key}", settings.IDEMPOTENCY_TTL_SECONDS, json.dumps(result))
    return result
