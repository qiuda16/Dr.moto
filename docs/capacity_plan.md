# Capacity & Data Retention Plan (Initial)

> Date: 2025-12-17  
> This is a working plan; update as metrics become available.

## 1. Data Growth Assumptions (example)
- Work orders: 50–300/day (single store)
- Media: 5–20 files/work order, average 500KB–3MB
- Status logs: 10–30 events/work order
- Audit logs: 5–20 events/work order
- Payments: 1–2/work order (incl refunds)

## 2. Retention
- Transactional records (work orders, payments): 5+ years (business/legal dependent)
- Audit logs: 1–2 years online, then archive
- Media objects: 1–2 years hot, then cold storage / lifecycle policy

## 3. Database Strategy
- Keep Odoo Postgres focused on transactional truth.
- High-volume logs MAY move to separate store later (ClickHouse/ELK).
- Partition candidates (monthly):
  - wo_status_log
  - audit_log
  - event_outbox (if used)

## 4. Performance Red Lines
- Payment callback handler must return quickly (no long blocking calls).
- Inventory posting should be transactional; use MQ for downstream notifications.

## 5. Backup / Restore
- Daily full backup; test restore at least monthly.
- Define target RPO/RTO:
  - RPO: 24h (initial), improve to 1h later
  - RTO: 2–4h (initial), improve to 1h later
