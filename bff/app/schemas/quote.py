from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from ..core.text import compact_whitespace


class QuoteItem(BaseModel):
    item_type: str = Field(default="service")
    code: Optional[str] = None
    name: str
    qty: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("name cannot be empty")
        return normalized


class QuoteVersionCreate(BaseModel):
    items: List[QuoteItem]
    note: Optional[str] = None


class QuoteVersionResponse(BaseModel):
    work_order_id: str
    version: int
    status: str
    is_active: bool
    amount_total: float
    items: List[QuoteItem]
