#!/usr/bin/env bash
set -euo pipefail
# POC-1: Inventory Issue/Return Idempotency
BFF_BASE_URL="${BFF_BASE_URL:-http://localhost:8080}"
STAFF_TOKEN="${STAFF_TOKEN:?STAFF_TOKEN is required}"
WORK_ORDER_ID="${WORK_ORDER_ID:?WORK_ORDER_ID is required}"
IDEMPOTENCY_KEY="${IDEMPOTENCY_KEY:-WO:${WORK_ORDER_ID}:ISSUE:POC1}"
ISSUE_PAYLOAD_JSON="${ISSUE_PAYLOAD_JSON:-{}}"
RETURN_PAYLOAD_JSON="${RETURN_PAYLOAD_JSON:-{}}"

echo "[POC-INV] Issue parts (1st call)..."
curl -sf -X POST "${BFF_BASE_URL}/bo/workorders/${WORK_ORDER_ID}/issue" \
  -H "Authorization: Bearer ${STAFF_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -d "${ISSUE_PAYLOAD_JSON}" | head -c 800

echo
echo "[POC-INV] Issue parts (2nd call, same idempotency key)..."
curl -sf -X POST "${BFF_BASE_URL}/bo/workorders/${WORK_ORDER_ID}/issue" \
  -H "Authorization: Bearer ${STAFF_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -d "${ISSUE_PAYLOAD_JSON}" | head -c 800

echo
echo "[POC-INV] Return parts..."
RETURN_KEY="WO:${WORK_ORDER_ID}:RETURN:POC1"
curl -sf -X POST "${BFF_BASE_URL}/bo/workorders/${WORK_ORDER_ID}/return" \
  -H "Authorization: Bearer ${STAFF_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: ${RETURN_KEY}" \
  -d "${RETURN_PAYLOAD_JSON}" | head -c 800

echo
echo "[POC-INV] EXPECT:"
echo "1) One posted Odoo picking for IDEMPOTENCY_KEY."
echo "2) Duplicate issue call returns same result without duplication."
echo "3) WO part lines reflect issued/returned quantities."
