# Security Baseline

> Date: 2025-12-17  
> Applies to: BFF, Odoo, Clients

## 1. Authentication
### Customer (WeChat mini-program)
- WeChat code -> BFF issues token (JWT or session token).
- Token MUST be short-lived; refresh strategy TBD.

### Staff
- Staff auth can be via BFF (preferred) or Odoo users.
- All staff endpoints MUST enforce RBAC server-side.

## 2. Authorization (RBAC + Data Scope)
- Default data scope: staff can only access `shop_id` bound records.
- Privileged actions require OWNER/ADMIN approval:
  - price changes after quote confirmation
  - cancel after any stock/payment events
  - refunds and reversals

## 3. Secrets Management
- No secrets in git.
- Use `.env` for local; secrets manager for production.

## 4. Logging and PII Masking
- MUST mask phone numbers, payment identifiers (partial), and tokens in logs.
- Store payment callback payloads **redacted** where required, retaining enough for audit.

## 5. Webhooks (WeChat Payment Callback)
- MUST verify signature / authenticity per provider requirements.
- MUST be idempotent.
- MUST protect against replay (use provider timestamps/nonces where available).

## 6. Transport Security
- TLS required in staging/prod.
- Internal service-to-service calls SHOULD also use TLS or private network with mTLS (phase 2).

## 7. Audit
- Any privileged action MUST create an audit_log record:
  - who, when, what, entity_type/id, before/after summary, trace_id
