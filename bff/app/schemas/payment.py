from pydantic import BaseModel, Field
from typing import Optional

class PaymentCreate(BaseModel):
    work_order_id: str
    amount: float = Field(..., gt=0)
    transaction_id: str

class PaymentIntentCreate(BaseModel):
    work_order_id: str
    amount: float = Field(..., gt=0)
    provider: str = "wechat"

class PaymentIntentResponse(BaseModel):
    payment_id: str
    payment_url: str
    status: str

class PaymentCallback(BaseModel):
    payment_id: str
    status: str
    transaction_id: str
    provider_ref: Optional[str] = None
