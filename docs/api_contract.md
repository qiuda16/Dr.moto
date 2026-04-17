# API Contract (Freezed)

> Date: 2025-12-18
> Status: Freezed (Matches Code Implementation)
> Format: REST + JSON

## Common Headers
- `Authorization: Bearer <token>`
- `Idempotency-Key: <key>` (required for critical actions)
- `X-Trace-Id: <trace>` (optional)

## Endpoints

### Health
- `GET /health`

### Auth
- `POST /auth/token`

### MP Customer Auth
- `POST /mp/customer/auth/wechat-login`
- `POST /mp/customer/auth/bind`
- `POST /mp/customer/auth/refresh`
- `POST /mp/customer/auth/logout`
- `GET /mp/customer/me`

### MP Customer Vehicle
- `GET /mp/customer/vehicles`
- `GET /mp/customer/home?vehicle_id={vehicleId}`
- `GET /mp/customer/vehicles/{vehicle_id}/health-records`
- `GET /mp/customer/vehicles/{vehicle_id}/maintenance-orders?page=1&size=20`
- `GET /mp/customer/maintenance-orders/{order_id}`
- `GET /mp/customer/vehicles/{vehicle_id}/recommended-services`
- `GET /mp/customer/vehicles/{vehicle_id}/knowledge-docs?category=...`
- `GET /mp/customer/subscriptions`
- `PUT /mp/customer/subscriptions`

### Work Orders (MP/Customer/Staff)
- `POST /mp/workorders/create`
- `GET /mp/workorders/{id}`
- `GET /mp/workorders/search?plate={plate}`
- `POST /mp/workorders/{id}/upload` (Media)

### Inventory (Staff)
- `POST /mp/inventory/issue`
  - Payload: `{ "work_order_id": "...", "product_id": 1, "quantity": 1 }`

### Payments
- `POST /mp/payments/create_intent`
  - Payload: `{ "work_order_id": "...", "amount": 100.0, "provider": "mock" }`
- `GET /mp/payments/mock_gateway` (HTML UI)
- `POST /mp/payments/mock_confirm` (Callback)

### Edge Events
- `POST /events/ingest`
- `GET /events/`

### Ops
- `POST /media/upload_base64`
