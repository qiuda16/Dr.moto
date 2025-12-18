#!/usr/bin/env bash
set -euo pipefail

# Smoke test placeholders.
# Expected env vars:
#   BFF_BASE_URL (e.g., http://localhost:8080)
#   ODOO_BASE_URL (e.g., http://localhost:8069)

BFF_BASE_URL="${BFF_BASE_URL:-http://localhost:8080}"

echo "[SMOKE] BFF health..."
curl -sf "$BFF_BASE_URL/health" | head -c 500 || (echo "BFF health failed" && exit 1)

echo
echo "[SMOKE] Done (extend this script with authenticated flows once APIs exist)."
