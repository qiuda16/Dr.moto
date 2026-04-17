from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
import logging
import json

from ..schemas.inventory import InventoryIssue
from ..integrations.odoo import odoo_client
from ..core.security import require_roles
from ..core.db import get_db
from ..models import WorkOrder
from ..schemas.auth import User
from ..core.config import settings
from ..core.store import resolve_store_id
import redis

router = APIRouter(prefix="/mp/inventory", tags=["Inventory"])
logger = logging.getLogger("bff")
redis_client = redis.Redis.from_url(settings.REDIS_URL)

@router.post("/issue")
async def issue_part(
    issue: InventoryIssue, 
    db: Session = Depends(get_db), 
    request: Request = None,
    current_user: User = Depends(require_roles(["admin", "manager", "keeper"]))
):
    store_id = resolve_store_id(request, current_user)
    idem_key = None
    if request:
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            cached = redis_client.get(f"idempotency:inv:issue:{store_id}:{idem_key}")
            if cached:
                return json.loads(cached.decode("utf-8"))

    # 1. Resolve Work Order
    # We assume work_order_id is the UUID from our DB
    wo = db.query(WorkOrder).filter(WorkOrder.uuid == issue.work_order_id, WorkOrder.store_id == store_id).first()
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
        
    result = {"status": "success", "message": "Part issued and stock move created"}
    if idem_key:
        redis_client.setex(
            f"idempotency:inv:issue:{store_id}:{idem_key}",
            settings.IDEMPOTENCY_TTL_SECONDS,
            json.dumps(result),
        )
    return result

@router.get("/products")
async def search_products(
    query: str = "",
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper", "staff"]))
):
    """Search products in Odoo (Live proxy)."""
    try:
        domain = [['name', 'ilike', query]] if query else []
        fields = ['id', 'name', 'list_price', 'standard_price', 'qty_available', 'uom_id']
        products = odoo_client.execute_kw('product.product', 'search_read', [domain], {'fields': fields, 'limit': limit})
        return products
    except Exception as e:
        logger.error(f"Product search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search products")


@router.get("/products/page")
async def search_products_page(
    query: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "manager", "keeper", "staff"]))
):
    """Paginated product search in Odoo."""
    try:
        domain = [['name', 'ilike', query]] if query else []
        total = odoo_client.execute_kw('product.product', 'search_count', [domain])
        offset = (page - 1) * size
        fields = ['id', 'name', 'list_price', 'standard_price', 'qty_available', 'uom_id']
        products = odoo_client.execute_kw(
            'product.product',
            'search_read',
            [domain],
            {'fields': fields, 'limit': size, 'offset': offset}
        )
        return {
            "items": products,
            "page": page,
            "size": size,
            "total": total,
            "has_more": (offset + len(products)) < total,
        }
    except Exception as e:
        logger.error(f"Product paged search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search products")
