# Release Notes - 2026-03-29

## Overview

This release hardens the backend toward enterprise-grade operation readiness.

## Added

- Health probes:
  - `GET /health/live`
  - `GET /health/ready`
- Work order productivity endpoints:
  - `GET /mp/workorders/{id}/actions`
  - `GET /mp/workorders/{id}/timeline`
  - `GET /mp/workorders/search/page`
  - `GET /mp/workorders/list/page` (advanced filter + pagination)
  - `POST /mp/workorders/bulk/update-status` (bulk workflow action)
- Quote version endpoints:
  - `POST /mp/quotes/{work_order_id}/versions`
  - `POST /mp/quotes/{work_order_id}/{version}/publish`
  - `POST /mp/quotes/{work_order_id}/{version}/confirm`
  - `POST /mp/quotes/{work_order_id}/{version}/reject`
  - `GET /mp/quotes/{work_order_id}`
- Inventory paged search:
  - `GET /mp/inventory/products/page`
- Document generation endpoint (already enabled):
  - `GET /mp/workorders/{id}/documents/{doc_type}`

## Improved

- Strict status transition checks in BFF (`409` on invalid transition).
- Idempotency protection:
  - work order creation
  - inventory issue
  - payment intent creation
- Duplicate transaction handling in payment record endpoint.
- Unified error body with `trace_id` and stable error code.
- Request tracing and latency response headers.
- Login rate limiting (IP based) on `/auth/token`.
- Dashboard KPI endpoint: `GET /mp/dashboard/summary`.
- DB engine pooling is now configurable (`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`, `pre_ping`).
- Odoo integration now has timeout + retry/backoff for better resilience on transient failures.
- Startup schema initialization is now environment-safe via `DB_AUTO_CREATE_TABLES` (disabled by policy in production).
- Production startup validation can fail-fast on weak/default secrets (`STRICT_STARTUP_VALIDATION`).
- BFF container runtime now enforces UTF-8 locale/IO defaults to improve Chinese text handling consistency.
- Added versioned SQL migration framework (`bff/migrations/versions` + `app.core.migrations`) and migration runner script (`scripts/db_migrate.ps1`).
- Updated production preflight script to use explicit admin credentials (no hardcoded default password).
- Added configurable structured logging (`LOG_FORMAT=json|plain`, `LOG_LEVEL`) with trace metadata output.
- Added Prometheus metrics endpoint with HTTP request counters/latency/in-flight gauges (`/metrics`).
- Added one-command release gate script (`scripts/release_gate.ps1`) to standardize build + migrate + preflight + smoke.
- Added operations scripts for alert evaluation, failure drill, and rollback (`alert_check.ps1`, `failure_drill.ps1`, `rollback_release.ps1`).
- Fixed Odoo health probing to use active connectivity check (`ping`) instead of cached authentication state.
- Added store-level data isolation foundation (`store_id` scope on core tables and scoped API queries via `X-Store-Id`/`store_id`).
- Added store isolation validation test case and smoke support for explicit store targeting (`-StoreId`).
- Added payment integration skeleton: configurable provider switch (`mock/wechat`), signed webhook callback endpoint, and payment event persistence.
- WeChat path now includes signed Native prepay request integration point (`/v3/pay/transactions/native`) with merchant key-based authorization.
- WeChat callback verification now supports platform certificate signature headers (`Wechatpay-*`) with shared-secret fallback.
- Added final production SOP document covering release/drill/rollback operations.
- Added alert report persistence (`scripts/alert_check.ps1` now writes JSON reports to `infra/reports/alerts`).

## Validation

- Unit tests: pass.
- Containerized smoke test: pass.
- Existing routes remain compatible for current clients.
