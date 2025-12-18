from pydantic import BaseModel

class InventoryIssue(BaseModel):
    work_order_id: str
    product_id: int
    quantity: float
