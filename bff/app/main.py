from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager
import uuid
import logging
import time
from datetime import datetime, timezone

from .core.config import settings
from .core.db import engine, Base, get_db
from .core.logging import setup_logging
from .core.metrics import (
    APP_INFO,
    HTTP_IN_PROGRESS,
    HTTP_REQUEST_LATENCY_SECONDS,
    HTTP_REQUEST_TOTAL,
    metrics_content,
    metrics_content_type,
)
from .core.migrations import apply_pending_migrations, pending_versions
from .integrations.odoo import odoo_client

# Import Routers
from .routers import work_orders, payments, ops, auth, events, inventory, knowledge, quotes, dashboard, catalog, customer_app, ai_ops, ai_assistant, settings as app_settings

# Initialize Logging
setup_logging()
logger = logging.getLogger("bff")

def collect_production_startup_issues() -> list[str]:
    issues: list[str] = []
    if settings.SECRET_KEY == "your-secret-key-change-me-in-production":
        issues.append("SECRET_KEY is using default value")
    if settings.ADMIN_PASSWORD == "change_me_now" and not settings.ADMIN_PASSWORD_HASH:
        issues.append("BFF admin password is using default value")
    if settings.ENABLE_DEV_ENDPOINTS:
        issues.append("BFF_ENABLE_DEV_ENDPOINTS must be false in production")
    if settings.ENABLE_MOCK_PAYMENT:
        issues.append("BFF_ENABLE_MOCK_PAYMENT must be false in production")
    if settings.PAYMENT_PROVIDER == "mock":
        issues.append("BFF_PAYMENT_PROVIDER must not be mock in production")
    if not settings.WEBHOOK_SHARED_SECRET:
        issues.append("BFF_WEBHOOK_SHARED_SECRET must be configured in production")
    if not settings.PAYMENT_WEBHOOK_SECRET:
        issues.append("BFF_PAYMENT_WEBHOOK_SECRET must be configured in production")

    if settings.PAYMENT_PROVIDER == "wechat":
        wechat_required = {
            "BFF_WECHAT_MCH_ID": settings.WECHAT_MCH_ID,
            "BFF_WECHAT_APP_ID": settings.WECHAT_APP_ID,
            "BFF_WECHAT_API_V3_KEY": settings.WECHAT_API_V3_KEY,
            "BFF_WECHAT_CERT_SERIAL_NO": settings.WECHAT_CERT_SERIAL_NO,
            "BFF_WECHAT_NOTIFY_URL": settings.WECHAT_NOTIFY_URL,
        }
        for key, value in wechat_required.items():
            if not value:
                issues.append(f"{key} must be configured when PAYMENT_PROVIDER=wechat")
        if not settings.WECHAT_MCH_PRIVATE_KEY_PEM and not settings.WECHAT_MCH_PRIVATE_KEY_PATH:
            issues.append(
                "BFF_WECHAT_MCH_PRIVATE_KEY_PEM or BFF_WECHAT_MCH_PRIVATE_KEY_PATH must be configured when PAYMENT_PROVIDER=wechat"
            )

    return issues

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production:
        startup_issues = collect_production_startup_issues()
        if startup_issues:
            message = f"Production startup validation failed: {', '.join(startup_issues)}"
            if settings.STRICT_STARTUP_VALIDATION:
                logger.error(message)
                raise RuntimeError(message)
            logger.warning(message)

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured on startup (auto-create enabled).")
    else:
        logger.info("Skipping automatic table creation (auto-create disabled).")

    pending = pending_versions(engine)
    if settings.AUTO_APPLY_MIGRATIONS:
        applied = apply_pending_migrations(engine)
        if applied:
            logger.info("Applied migrations on startup: %s", ",".join(applied))
        else:
            logger.info("No pending migrations on startup.")
    elif pending:
        logger.warning(
            "Pending DB migrations detected but auto-apply is disabled: %s",
            ",".join(pending),
        )

    APP_INFO.labels(version=settings.VERSION, env=settings.ENV).set(1)
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    start_at = time.time()
    HTTP_IN_PROGRESS.inc()
    try:
        response = await call_next(request)
        process_ms = int((time.time() - start_at) * 1000)
        process_seconds = process_ms / 1000.0
        route_path = request.url.path
        route = request.scope.get("route")
        if route and getattr(route, "path", None):
            route_path = route.path

        HTTP_REQUEST_TOTAL.labels(
            method=request.method,
            path=route_path,
            status_code=str(response.status_code),
        ).inc()
        HTTP_REQUEST_LATENCY_SECONDS.labels(
            method=request.method,
            path=route_path,
        ).observe(process_seconds)

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time-Ms"] = str(process_ms)
        logger.info(
            "request handled",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": process_ms,
            },
        )
        return response
    finally:
        HTTP_IN_PROGRESS.dec()


@app.get(settings.METRICS_PATH, include_in_schema=False)
async def metrics_endpoint():
    if not settings.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics endpoint disabled")
    return Response(content=metrics_content(), media_type=metrics_content_type())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
            "trace_id": trace_id,
            "time": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    logger.exception("unhandled exception", extra={"trace_id": trace_id})
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
            },
            "trace_id": trace_id,
            "time": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/health/live")
async def liveness_probe():
    return {"status": "alive", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "db": f"{e}"})

    if not odoo_client.ping():
        return JSONResponse(status_code=503, content={"status": "not_ready", "odoo": "unavailable"})

    return {"status": "ready", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check DB connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Odoo connection
    odoo_status = "ok" if odoo_client.ping() else "error"
    overall = "ok" if db_status == "ok" and odoo_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "odoo": odoo_status,
        "version": settings.VERSION,
        "env": settings.ENV,
        "time": datetime.now(timezone.utc).isoformat(),
    }

# Include Routers
app.include_router(auth.router)
app.include_router(work_orders.router)
app.include_router(payments.router)
app.include_router(ops.router)
app.include_router(events.router)
app.include_router(inventory.router)
app.include_router(knowledge.router)
app.include_router(quotes.router)
app.include_router(dashboard.router)
app.include_router(catalog.router)
app.include_router(app_settings.router)
app.include_router(customer_app.router)
app.include_router(ai_ops.router)
app.include_router(ai_assistant.router)
