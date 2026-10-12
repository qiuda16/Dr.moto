from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from ..core.text import compact_whitespace, normalize_text


class WebsiteLeadCreate(BaseModel):
    name: str = Field(..., max_length=80)
    contact: str = Field(..., max_length=120)
    identity: str = Field(default="rider", max_length=40)
    message: Optional[str] = Field(default=None, max_length=500)
    source_page: Optional[str] = Field(default=None, max_length=255)
    store_id: str = Field(default="default", max_length=64)

    @field_validator("name", "contact")
    @classmethod
    def require_text(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized

    @field_validator("identity", "message", "source_page", "store_id")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return normalize_text(value) if value is not None else value


class WebsiteLeadUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=40)
    assigned_to: Optional[str] = Field(default=None, max_length=80)
    notes: Optional[str] = Field(default=None, max_length=500)


class TrialWorkOrderCreate(BaseModel):
    source_type: str = Field(..., pattern="^(lead|appointment)$")
    source_id: int
    customer_id: Optional[str] = Field(default=None, max_length=32)
    vehicle_plate: Optional[str] = Field(default=None, max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)


class OfflinePaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., max_length=40)
    payer_note: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=255)
    received_at: Optional[datetime] = None

    @field_validator("payment_method", "idempotency_key")
    @classmethod
    def normalize_text_value(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = normalize_text(value)
        if not normalized:
            raise ValueError("value cannot be empty")
        return normalized


class TrialInboxItem(BaseModel):
    source_type: str
    id: int
    status: str
    title: str
    contact: Optional[str] = None
    identity: Optional[str] = None
    vehicle_plate: Optional[str] = None
    preferred_date: Optional[datetime] = None
    message: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    converted_work_order_uuid: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
