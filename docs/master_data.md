# Master Data Rules

> Date: 2025-12-17

## 1. Identifiers and Uniqueness
### Customer
- Primary identifier: `phone`
- Uniqueness: `(shop_id, phone)` MUST be unique
- If WeChat unionid exists, link to customer as secondary identifier

### Vehicle
- Required: `plate_no`
- Uniqueness: `(shop_id, plate_no)` MUST be unique
- Optional: `vin` (if provided, may be unique globally or per shop)

## 2. Coding Standards
### Work Order Number (`wo_no`)
Format (recommended):
- `{
  SHOP_CODE
}-{YYYYMMDD}-{SEQ4}`
- Sequence resets daily per shop (implementation detail).

### Product / Service Codes
- Products managed in Odoo as SKU.
- Service/labor items MUST have stable `service_code` for reporting.
- Avoid renaming codes; prefer deprecating + new code.

## 3. Dictionaries (Enums)
### Work Order Status (MUST)
- DRAFT, CHECKIN, DIAGNOSING, QUOTED, IN_PROGRESS, READY, DELIVERED, CLOSED, CANCELLED

### Payment Channel (MVP)
- WECHAT, OFFLINE_CASH, OFFLINE_CARD, OFFLINE_TRANSFER

## 4. Dedupe and Merge Rules
- Customer merge requires admin role and creates an audit log entry.
- Vehicle reassignment to another customer is a privileged action and must be audited.
