from pydantic import BaseModel, Field
from typing import List, Optional


class WorkOrderBulkStatusUpdate(BaseModel):
    order_ids: List[str] = Field(..., min_length=1)
    target_status: str
    strict: bool = True


class WorkOrderBulkStatusResult(BaseModel):
    requested: int
    succeeded: int
    failed: int
    target_status: str
    success_order_ids: List[str]
    failed_items: List[dict]


class WorkOrderBulkDeleteRequest(BaseModel):
    order_ids: List[str] = Field(..., min_length=1)


class WorkOrderServiceSelectionUpdate(BaseModel):
    labor_price: Optional[float] = None
    suggested_price: Optional[float] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class WorkOrderServiceSelectionReorderRequest(BaseModel):
    selection_ids: List[int] = Field(..., min_length=1)
