from pydantic import BaseModel

class StatusUpdateWebhook(BaseModel):
    odoo_id: int
    new_status: str
    bff_uuid: str
