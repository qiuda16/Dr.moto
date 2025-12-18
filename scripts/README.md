# Scripts

> Updated: 2025-12-17

## Smoke tests
- `smoke_test.sh` — basic health checks (extend as APIs land)

## POCs (Preparation Gate)
- `poc_inventory.sh` — inventory issue/return idempotency (POC-1)
- `poc_payment.sh` — WeChat callback idempotency (POC-2)
- `poc_ai_readonly.sh` — AI CS read-only integration (POC-3)

## Usage
Each script documents required environment variables.

Example:
```bash
export BFF_BASE_URL="http://localhost:8080"
export STAFF_TOKEN="..."
export WORK_ORDER_ID="..."
bash scripts/poc_inventory.sh
```
