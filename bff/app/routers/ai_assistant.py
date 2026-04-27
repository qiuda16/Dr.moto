from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.security import require_roles
from ..schemas.auth import User

router = APIRouter(prefix="/ai/assistant", tags=["AI Assistant"])
logger = logging.getLogger("bff")
AI_PROXY_SEMAPHORE = asyncio.Semaphore(max(1, settings.AI_PROXY_MAX_INFLIGHT))


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


def _build_proxy_fallback(message: str, reason: str) -> dict[str, Any]:
    lowered = (message or "").lower()
    if "车型" in lowered or "bmw" in lowered or "宝马" in lowered or "catalog" in lowered:
        text = "我这边正在高峰处理中，但已收到你的查询。请再发一次品牌或车型关键词，我优先返回车型清单。"
    elif "工单" in lowered or "车牌" in lowered or "交付" in lowered:
        text = "我已收到你的门店查询请求，当前系统繁忙。请再发一次车牌/工单号，我会优先返回结果。"
    else:
        text = "我已经收到你的问题，当前系统繁忙。请稍后重试，我会优先处理你的这条请求。"
    return {
        "response": text,
        "suggested_actions": [],
        "action_cards": [],
        "sources": [],
        "debug": {"proxy_fallback": True, "reason": reason},
    }


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


def _looks_like_low_info_query(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return True
    return text in {
        "帮我查下",
        "查一下",
        "查下",
        "看一下",
        "看看",
        "查查",
        "help",
        "check",
        "query",
    }


def _build_proxy_fallback_v2(message: str, reason: str) -> dict[str, Any]:
    lowered = str(message or "").lower()
    if _looks_like_low_info_query(message):
        text = "我这边先没拿到足够线索。你给我客户名、车牌或工单号任意一个，我马上继续查。"
    elif (
        any(token in lowered for token in ["create", "update", "write", "field", "fields", "step", "steps"])
        or ("?" in lowered and any(token in lowered for token in ["quote", "order", "customer", "vehicle"]))
    ):
        text = "当前系统忙碌，我先给你可执行写入指引：告诉我目标对象（客户/车牌/工单）和要变更字段，我先回预写入清单，确认后再执行。"
    elif any(token in lowered for token in ["bmw", "catalog", "model"]):
        text = "我这边正在高峰处理中，但已收到你的查询。请再发一次品牌或车型关键词，我优先返回车型清单。"
    elif any(token in lowered for token in ["ready", "quoted", "in progress", "order", "workorder"]):
        text = "我已收到你的门店查询请求，当前系统繁忙。请再发一次车牌或工单号，我会优先返回结果。"
    else:
        text = "我已经收到你的问题，当前系统繁忙。请稍后重试，我会优先处理你的这条请求。"
    return {
        "response": text,
        "suggested_actions": [],
        "action_cards": [],
        "sources": [],
        "debug": {"proxy_fallback": True, "reason": reason},
    }


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
        "context": {**enriched_context, "_skip_ai_enrich": True},
    }
    headers = {"X-Store-Id": request.headers.get("X-Store-Id", settings.DEFAULT_STORE_ID)}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    if settings.WEBHOOK_SHARED_SECRET:
        headers["X-Internal-Secret"] = settings.WEBHOOK_SHARED_SECRET

    acquired = False
    try:
        try:
            await asyncio.wait_for(AI_PROXY_SEMAPHORE.acquire(), timeout=max(0.1, settings.AI_PROXY_QUEUE_WAIT_SECONDS))
            acquired = True
        except TimeoutError:
            return _build_proxy_fallback_v2(payload.message, reason="bff_proxy_overloaded")

        timeout = httpx.Timeout(
            connect=3.0,
            read=max(3.0, float(settings.AI_PROXY_TIMEOUT_SECONDS)),
            write=10.0,
            pool=max(0.1, float(settings.AI_PROXY_POOL_TIMEOUT_SECONDS)),
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            if needs_prefetch and payload.message.strip() and not _looks_like_low_info_query(payload.message):
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
                        timeout=max(1.0, float(settings.AI_PREFETCH_TIMEOUT_SECONDS)),
                    )
                    context_response.raise_for_status()
                    prefetched = context_response.json() or {}
                    if isinstance(prefetched, dict):
                        body["context"] = {**prefetched, **enriched_context, "_skip_ai_enrich": True}
                except httpx.HTTPError as exc:
                    logger.warning("assistant context prefetch failed: %s", exc)

            # Overview prefetch is expensive (multiple list APIs). Only do this for
            # store-ops intent, otherwise let AI handle non-ops questions directly.
            should_prefetch_overview = _looks_like_store_ops_query(payload.message) and not body["context"].get(
                "store_overview"
            )
            if should_prefetch_overview:
                try:
                    overview_response = await client.get(
                        "http://127.0.0.1:8080/mp/dashboard/overview",
                        headers=headers,
                        timeout=max(1.0, float(settings.AI_PREFETCH_TIMEOUT_SECONDS)),
                    )
                    overview_response.raise_for_status()
                    overview_payload = overview_response.json() or {}
                    if isinstance(overview_payload, dict):
                        existing_overview = dict((body.get("context") or {}).get("store_overview") or {})
                        ready_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "ready", "page": 1, "size": 20},
                            headers=headers,
                            timeout=max(1.0, float(settings.AI_PREFETCH_TIMEOUT_SECONDS)),
                        )
                        ready_orders_response.raise_for_status()
                        ready_orders = (ready_orders_response.json() or {}).get("items") or []

                        quoted_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "quoted", "page": 1, "size": 20},
                            headers=headers,
                            timeout=max(1.0, float(settings.AI_PREFETCH_TIMEOUT_SECONDS)),
                        )
                        quoted_orders_response.raise_for_status()
                        quoted_orders = (quoted_orders_response.json() or {}).get("items") or []

                        in_progress_orders_response = await client.get(
                            "http://127.0.0.1:8080/mp/workorders/list/page",
                            params={"status": "in_progress", "page": 1, "size": 20},
                            headers=headers,
                            timeout=max(1.0, float(settings.AI_PREFETCH_TIMEOUT_SECONDS)),
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
                            "_skip_ai_enrich": True,
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
    except httpx.TimeoutException as exc:
        logger.warning("assistant chat proxy timeout: %s", exc)
        return _build_proxy_fallback_v2(payload.message, reason="ai_timeout")
    except httpx.HTTPError as exc:
        logger.error("assistant chat proxy failed: %s", exc)
        return _build_proxy_fallback_v2(payload.message, reason="ai_unavailable")
    finally:
        if acquired:
            AI_PROXY_SEMAPHORE.release()
