#!/usr/bin/env bash
set -euo pipefail
# POC-3: AI CS Read-only Integration
AI_BASE_URL="${AI_BASE_URL:-http://localhost:8090}"
QUESTION="${QUESTION:-"门店营业时间是什么？"}"

echo "[POC-AI] /chat..."
curl -sf -X POST "${AI_BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d "{"message": ${QUESTION} }" | head -c 1200

echo
echo "[POC-AI] /search_kb..."
curl -sf -X POST "${AI_BASE_URL}/search_kb" \
  -H "Content-Type: application/json" \
  -d "{"query": ${QUESTION} }" | head -c 1200

echo
echo "[POC-AI] EXPECT:"
echo "1) KB-grounded answers."
echo "2) AI service exposes no write endpoints for transactions."
echo "3) Any WO lookup is via BFF read-only endpoints."
