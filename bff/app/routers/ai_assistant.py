import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.security import require_roles
from ..schemas.auth import User

router = APIRouter(prefix="/ai/assistant", tags=["AI Assistant"])
logger = logging.getLogger("bff")


class AssistantChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class AssistantChatResponse(BaseModel):
    response: str
    suggested_actions: list[str] = Field(default_factory=list)
    action_cards: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    debug: dict[str, Any] | None = None


def _looks_like_store_ops_query(message: str) -> bool:
    lowered = str(message or "").lower()
    keywords = [
        "待交付",
        "交付",
        "ready",
        "待施工",
        "施工",
        "in progress",
        "报价待确认",
        "报价",
        "quoted",
        "超期",
        "overdue",
        "加急",
        "urgent",
        "车牌",
        "车牌号",
        "哪些工单",
        "哪些车",
        "哪些订单",
        "今天先盯什么",
        "今天门店最应该先盯什么",
        "最应该先盯什么",
        "优先盯什么",
    ]
    return any(keyword in lowered for keyword in keywords)


def _detect_identifiers(message: str) -> tuple[str, str]:
    text = str(message or "")
    normalized = text.upper()
    cn_plate_match = re.search(
        r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6}",
        normalized,
    )
    plate_match = cn_plate_match or re.search(r"\b[A-Z0-9-]*\d+[A-Z0-9-]*\b", normalized)
    work_order_match = re.search(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", text.lower())
    return (
        plate_match.group(0) if plate_match else "",
        work_order_match.group(0) if work_order_match else "",
    )


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    payload: AssistantChatRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "manager", "staff", "keeper", "cashier"])),
):
    enriched_context = dict(payload.context or {})
    needs_prefetch = not any(
        enriched_context.get(key)
        for key in [
            "matched_customer",
            "matched_vehicle",
            "matched_work_order",
            "vehicle_catalog_models",
            "customers",
            "vehicles",
            "work_orders",
            "parts",
            "recommended_services",
            "knowledge_docs",
        ]
    )

    body = {
        "user_id": payload.user_id or current_user.username,
        "message": payload.message,
        "context": enriched_context,
    }
    headers = {"X-Store-Id": request.headers.get("X-Store-Id", settings.DEFAULT_STORE_ID)}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    if settings.WEBHOOK_SHARED_SECRET:
        headers["X-Internal-Secret"] = settings.WEBHOOK_SHARED_SECRET

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if needs_prefetch and payload.message.strip():
                try:
                    plate, work_order_id = _detect_identifiers(payload.message.strip())
                    prefetch_params: dict[str, Any]
                    if work_order_id:
                        prefetch_params = {"work_order_id": work_order_id}
                    elif plate:
                        prefetch_params = {"plate": plate}
                    else:
                        prefetch_params = {"query": payload.message.strip()}
                    context_response = await client.get(
                        "http://127.0.0.1:8080/ai/ops/context",
                        params=prefetch_params,
                        headers=headers,
                    )
                    context_response.raise_for_status()
                    prefetched = context_response.json() or {}
                    if isinstance(prefetched, dict):
                        body["context"] = {**prefetched, **enriched_context}
                except httpx.HTTPError as exc:
                    logger.warning("assistant context prefetch failed: %s", exc)

            should_prefetch_overview = _looks_like_store_ops_query(payload.message) or not body["context"].get("store_overview")
            if should_prefetch_overview:
                try:
                    overview_response = await client.get(
                        "http://127.0.0.1:8080/mp/dashboard/overview",
                        headers=headers,
                    )
                    overview_response.raise_for_status()
                    overview_payload = overview_response.json() or {}
                    if isinstance(overview_payload, dict):
                        existing_overview = dict((body.get("context") or {}).get("store_overview") or {})
                        ready_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "ready", "page": 1, "size": 20},
                            headers=headers,
                        )
                        ready_orders_response.raise_for_status()
                        ready_orders = (ready_orders_response.json() or {}).get("items") or []

                        quoted_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "quoted", "page": 1, "size": 20},
                            headers=headers,
                        )
                        quoted_orders_response.raise_for_status()
                        quoted_orders = (quoted_orders_response.json() or {}).get("items") or []

                        in_progress_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "in_progress", "page": 1, "size": 20},
                            headers=headers,
                        )
                        in_progress_orders_response.raise_for_status()
                        in_progress_orders = (in_progress_orders_response.json() or {}).get("items") or []

                        merged_overview = {
                            **overview_payload,
                            **existing_overview,
                            "recent_orders": existing_overview.get("recent_orders")
                            or ((overview_payload.get("recent") or {}).get("orders") or []),
                            "ready_orders": existing_overview.get("ready_orders") or ready_orders,
                            "quoted_orders": existing_overview.get("quoted_orders") or quoted_orders,
                            "in_progress_orders": existing_overview.get("in_progress_orders") or in_progress_orders,
                        }
                        body["context"] = {
                            **(body.get("context") or {}),
                            "store_overview": merged_overview,
                        }
                except httpx.HTTPError as exc:
                    logger.warning("assistant store overview prefetch failed: %s", exc)

            response = await client.post(
                f"{settings.AI_URL}/chat",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        return {
            "response": data.get("response", ""),
            "suggested_actions": data.get("suggested_actions", []) or [],
            "action_cards": data.get("action_cards", []) or [],
            "sources": data.get("sources", []) or [],
            "debug": data.get("debug"),
        }
    except httpx.HTTPError as exc:
        logger.error("assistant chat proxy failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI assistant unavailable") from exc
