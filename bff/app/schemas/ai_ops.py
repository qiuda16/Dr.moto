from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AiActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AiActionResponse(BaseModel):
    status: str = "ok"
    action: str
    result: dict[str, Any]
    risk_level: str = "low"


class AiContextResponse(BaseModel):
    store_id: str
    query: str | None = None
    query_domains: list[str] = Field(default_factory=list)
    primary_domain: str | None = None
    source_hints: list[str] = Field(default_factory=list)
    retrieval_plan: list[str] = Field(default_factory=list)
    matched_customer: dict[str, Any] | None = None
    matched_vehicle: dict[str, Any] | None = None
    matched_work_order: dict[str, Any] | None = None
    customers: list[dict[str, Any]] = Field(default_factory=list)
    vehicles: list[dict[str, Any]] = Field(default_factory=list)
    vehicle_catalog_models: list[dict[str, Any]] = Field(default_factory=list)
    work_orders: list[dict[str, Any]] = Field(default_factory=list)
    recommended_services: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_docs: list[dict[str, Any]] = Field(default_factory=list)
    parts: list[dict[str, Any]] = Field(default_factory=list)
    write_capabilities: list[str] = Field(default_factory=list)
