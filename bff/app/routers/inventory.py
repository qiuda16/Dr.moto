from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ..schemas.inventory import InventoryIssue
from ..integrations.odoo import odoo_client
from ..core.security import get_current_user
from ..core.db import get_db
from ..models import WorkOrder

router = APIRouter(prefix="/mp/inventory", tags=["Inventory"])
logger = logging.getLogger("bff")

@router.post("/issue")
async def issue_part(
    issue: InventoryIssue, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    # 1. Resolve Work Order
    # We assume work_order_id is the UUID from our DB
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == issue.work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    odoo_id = wo.odoo_id
    
    # 2. Call Odoo
    try:
        # Args: [work_order_id, product_id, quantity]
        success = odoo_client.execute_kw(
            'drmoto.work.order', 
            'issue_part_bff', 
            [odoo_id, issue.product_id, issue.quantity]
        )
        
        if not success:
             raise HTTPException(status_code=400, detail="Failed to issue part in Odoo (Check logs or IDs)")
             
    except Exception as e:
        logger.error(f"Inventory issue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "message": "Part issued and stock move created"}

@router.get("/products")
async def search_products(query: str = "", limit: int = 10, current_user = Depends(get_current_user)):
    """Search products in Odoo (Live proxy)."""
    try:
        domain = [['name', 'ilike', query]] if query else []
        fields = ['id', 'name', 'list_price', 'standard_price', 'qty_available', 'uom_id']
        products = odoo_client.execute_kw('product.product', 'search_read', [domain], {'fields': fields, 'limit': limit})
        return products
    except Exception as e:
        logger.error(f"Product search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search products")
