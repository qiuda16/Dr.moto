# System Test Report

Date: 2026-04-08
Executor: Codex

## Scope

- Service health and container status
- BFF automated tests
- Frontend production builds
- Key business smoke tests
- AI query and AI write regression
- Sequential and concurrent stability checks

## Environment

- BFF: `http://127.0.0.1:18080`
- AI: `http://127.0.0.1:8001`
- Core model: `qwen3:8b`
- Context window: `40960`

## Results

### 1. Core services

- `infra-bff-1`: up and healthy
- `infra-ai-1`: up
- `infra-odoo-1`: up and healthy
- `infra-db-1`: up and healthy
- `infra-redis-1`: up and healthy
- `infra-minio-1`: up
- `infra-ocr_vl-1`: up

### 2. Automated backend tests

- Executed in container: `python3 -m pytest /app/tests -q`
- Result: `16 passed`

Notes:
- Test helpers were hardened to clear login rate-limit keys between cases.
- Customer mini-app auth test now uses unique WeChat login codes to avoid stale binding collisions.
- Bulk work-order status test was aligned with current business behavior.

### 3. Frontend builds

- `clients/cs_workspace`: passed
- `clients/web_staff`: passed
- `clients/web_display`: passed
- `clients/mp_customer`: passed
- `clients/mp_staff`: passed
- `clients/mp_customer_uni` (`build:h5`): passed

Notes:
- `clients/web_display` build script was fixed to call local Vite explicitly.
- `clients/web_display` runtime path was also corrected later in this round to use a dedicated public display endpoint instead of a staff-only authenticated endpoint.

### 4. Business smoke tests

- Health check: passed
- Admin login: passed
- Customer creation: passed
- Work-order creation: passed
- Work-order document rendering: passed
- Work-order actions endpoint: passed
- Quote create + publish: passed
- Dashboard summary: passed

### 5. AI regression

- Query test: `系统里有哪些宝马车型`
  - passed
  - `primary_domain=catalog`
  - `global_query_fast_path=true`

- Write test: `新建客户 系统测试客户0408 电话 13900004080`
  - passed
  - `write_executed=true`
  - `write_action=create_customer`
  - `risk_level=low`

### 6. Stability checks

- Sequential API loop:
  - 20 rounds of `/health` + `/mp/dashboard/summary` + `/mp/workorders/list/page`
  - result: all `200`

- Sequential AI query loop:
  - 8 rounds
  - result: all succeeded

- Sequential AI write loop:
  - 5 rounds
  - result: all succeeded

- Concurrent mixed load:
  - 6 parallel workers
  - each worker called dashboard summary, work-order page, AI query
  - result: all succeeded, no timeout, no 500

- Concurrent mixed load (heavier):
  - 12 parallel workers
  - each worker called dashboard summary, work-order page, AI query
  - result: all succeeded, no timeout, no 500

- AI long-context soak:
  - 2 same-session turns plus 1 follow-up recall question
  - latency observed: about `20.42s`, `29.74s`, `30.43s`
  - service remained healthy after test
  - recall quality did not meet desired standard: the final follow-up did not reliably retain the injected test identifier

## Fixes Made During Testing

- Updated:
  - `bff/tests/test_api.py`
  - `bff/tests/test_ai_ops.py`
  - `bff/tests/test_mp_customer_api.py`
  - `clients/web_display/package.json`
  - `bff/app/routers/work_orders.py`
  - `clients/web_display/src/App.vue`

## Non-AI Module Coverage

- A dedicated non-AI module report was added:
  - `docs/non_ai_module_test_report_2026-04-08.md`
- Covered modules:
  - `web_staff` dashboard, work orders, customers, inventory
  - `mp_customer`
  - `mp_staff`
  - `web_display`
- Representative endpoint regression and runtime-path verification passed after fixing the display board authorization mismatch.

## Residual Risks

- `cs_workspace` and `web_staff` still report large chunk warnings during build. This does not block runtime, but bundle splitting should be improved later.
- `mp_customer_uni` shows Sass deprecation warnings. Build output is currently usable.
- `web_display` dependency install reports moderate npm audit issues that are not blocking build, but should be reviewed before production hardening.
- AI long-session quality is not yet at a “strong memory assistant” level. Under multi-turn continuity tests, latency increased noticeably and recall was not reliable enough for strict long-dialogue expectations.
- Login rate limiting correctly protected the auth endpoint during aggressive concurrent-login testing. This is good for safety, but if you later need heavy automated login traffic, a separate test or service credential strategy should be used.

## Delivery Status

- Current status: usable and stable for core workflows
- No blocking crash or deadlock was reproduced in this test round
