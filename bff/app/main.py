from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import logging

from .core.config import settings
from .core.db import engine, Base, get_db
from .integrations.odoo import odoo_client

# Import Routers
from .routers import work_orders, payments, ops, auth, events, inventory, knowledge

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bff")

# Create Tables (MVP only; use Alembic for prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check DB connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Odoo connection
    odoo_uid = odoo_client.authenticate()
    odoo_status = "ok" if odoo_uid else "error"
    
    return {"status": "ok", "db": db_status, "odoo": odoo_status, "version": settings.VERSION}

# Include Routers
app.include_router(auth.router)
app.include_router(work_orders.router)
app.include_router(payments.router)
app.include_router(ops.router)
app.include_router(events.router)
app.include_router(inventory.router)
app.include_router(knowledge.router)
