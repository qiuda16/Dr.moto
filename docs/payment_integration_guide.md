# Payment Integration Guide

Updated: 2026-03-29

## 1. Current capability

- Provider mode switch via env: `mock` or `wechat` (skeleton).
- Payment intent endpoint: `POST /mp/payments/create_intent`
- Provider callback endpoint: `POST /mp/payments/webhook/{provider}`
- Callback signature header: `X-Payment-Signature` (HMAC-SHA256 over raw body, keyed by `BFF_PAYMENT_WEBHOOK_SECRET`)

## 2. Required environment variables

- `BFF_PAYMENT_PROVIDER=mock|wechat`
- `BFF_PAYMENT_WEBHOOK_SECRET=<secret>`
- For WeChat skeleton readiness:
  - `BFF_WECHAT_MCH_ID`
  - `BFF_WECHAT_APP_ID`
  - `BFF_WECHAT_API_V3_KEY`
  - `BFF_WECHAT_CERT_SERIAL_NO`
  - merchant private key from either:
    - `BFF_WECHAT_MCH_PRIVATE_KEY_PEM`
    - `BFF_WECHAT_MCH_PRIVATE_KEY_PATH`
  - `BFF_WECHAT_NOTIFY_URL`

## 3. Webhook payload contract

```json
{
  "payment_id": "provider callback id",
  "transaction_id": "PAY-XXXXXXXXXXXX",
  "status": "paid",
  "provider_ref": "optional external transaction reference"
}
```

## 4. Store-scoped callback

Send `X-Store-Id` to ensure callback is mapped to the correct store ledger.

## 5. Real WeChat request path

When `provider=wechat`, BFF signs and sends request to:

- `POST /v3/pay/transactions/native`

Current implementation returns WeChat `code_url` directly as `payment_url` in intent response.
