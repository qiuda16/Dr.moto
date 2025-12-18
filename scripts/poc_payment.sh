#!/usr/bin/env bash
set -euo pipefail
# POC-2: Payment Intent + Mock Confirm
BFF_BASE_URL="${BFF_BASE_URL:-http://localhost:8080}"
WORK_ORDER_ID="${WORK_ORDER_ID:?WORK_ORDER_ID is required}"

# 1. Login
echo "[POC-PAY] Logging in..."
TOKEN=$(curl -sf -X POST "${BFF_BASE_URL}/auth/token" \
  -d "username=staff&password=secret" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

AUTH_HEADER="Authorization: Bearer $TOKEN"

# 2. Create Intent
echo
echo "[POC-PAY] Create payment intent..."
# We use a random amount
AMOUNT=100.0

RESPONSE=$(curl -sf -X POST "${BFF_BASE_URL}/mp/payments/create_intent" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{\"work_order_id\":\"${WORK_ORDER_ID}\", \"amount\":${AMOUNT}, \"provider\":\"mock\"}")

echo "Response: $RESPONSE"
TRANS_ID=$(echo $RESPONSE | grep -o '"payment_id":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TRANS_ID" ]; then
  echo "Failed to get transaction ID"
  exit 1
fi

echo "Transaction ID: $TRANS_ID"

# 3. Confirm (Mock Callback)
echo
echo "[POC-PAY] Confirming payment (Mock Callback)..."
curl -sf -X POST "${BFF_BASE_URL}/mp/payments/mock_confirm" \
  -H "Content-Type: application/json" \
  -d "{\"transaction_id\":\"${TRANS_ID}\"}"

echo
echo "[POC-PAY] Done."
