from pydantic import BaseModel
from typing import Optional

class PaymentCreate(BaseModel):
    work_order_id: str
    amount: float
    transaction_id: str

class PaymentIntentCreate(BaseModel):
    work_order_id: str
    amount: float
    provider: str = "wechat"

class PaymentIntentResponse(BaseModel):
    payment_id: str
    payment_url: str
    status: str

class PaymentCallback(BaseModel):
    payment_id: str
    status: str
    transaction_id: str
