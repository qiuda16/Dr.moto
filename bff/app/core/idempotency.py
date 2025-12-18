from fastapi import Header, HTTPException, Request
from .config import settings
import redis
import json

# Global redis pool
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

async def verify_idempotency(
    request: Request,
    x_idempotency_key: str = Header(None, alias="X-Idempotency-Key")
):
    """
    Check if the request has already been processed.
    If yes, we should ideally return the cached response (not fully implemented here, just the check).
    If no, we lock the key.
    """
    if not x_idempotency_key:
        return # Optional for now, or make required for specific routes
        
    key = f"idempotency:{x_idempotency_key}"
    
    # Check if key exists
    cached = redis_client.get(key)
    if cached:
        # In a full implementation, we would return the saved response here.
        # For now, we just reject concurrent duplicates.
        raise HTTPException(status_code=409, detail="Request already processed (Idempotency Key)")
        
    # Lock the key for a duration (e.g. 24h)
    # We set a 'processing' state. 
    # The actual response storage would happen in a middleware or after request.
    redis_client.setex(key, 86400, "processing")
    
    return x_idempotency_key
