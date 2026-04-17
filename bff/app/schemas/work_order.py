from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional

from ..core.text import compact_whitespace

WORK_ORDER_CUSTOMER_ID_MAX = 32
WORK_ORDER_PLATE_MAX = 30
WORK_ORDER_DESCRIPTION_MAX = 500
WORK_ORDER_NOTE_MAX = 1000

class WorkOrderCreate(BaseModel):
    customer_id: str = Field(..., max_length=WORK_ORDER_CUSTOMER_ID_MAX)
    vehicle_plate: str = Field(..., max_length=WORK_ORDER_PLATE_MAX)
    description: str = Field(..., max_length=WORK_ORDER_DESCRIPTION_MAX)

    @field_validator("customer_id", "vehicle_plate", "description")
    @classmethod
    def normalize_fields(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("Field cannot be empty")
        return normalized

class WorkOrderResponse(BaseModel):
    id: str # Odoo ID or local Trace ID
    status: str
    data: Dict[str, Any]


class WorkOrderProcessRecordUpdate(BaseModel):
    symptom_draft: Optional[str] = Field(default=None, max_length=WORK_ORDER_NOTE_MAX)
    symptom_confirmed: Optional[str] = Field(default=None, max_length=WORK_ORDER_NOTE_MAX)
    quick_check: Optional[Dict[str, Any]] = None

    @field_validator("symptom_draft", "symptom_confirmed")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = compact_whitespace(value)
        return normalized or None


class WorkOrderProcessRecordResponse(BaseModel):
    work_order_id: str
    symptom_draft: Optional[str] = None
    symptom_confirmed: Optional[str] = None
    quick_check: Dict[str, Any] = Field(default_factory=dict)
