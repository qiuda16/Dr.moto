from pydantic import BaseModel
from typing import Dict, Any

class WorkOrderCreate(BaseModel):
    customer_id: str
    vehicle_plate: str
    description: str

class WorkOrderResponse(BaseModel):
    id: str # Odoo ID or local Trace ID
    status: str
    data: Dict[str, Any]
