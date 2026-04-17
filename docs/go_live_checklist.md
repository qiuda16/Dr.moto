# Go-Live Checklist (Store Operations)

Updated: 2026-03-29

## 1. Security

- Start from `infra/.env.prod.sample` and generate `infra/.env` for production.
- Replace all default secrets in `infra/.env`.
- Set `BFF_ENV=prod`.
- Set `BFF_ENABLE_DEV_ENDPOINTS=false`.
- Set `BFF_ENABLE_MOCK_PAYMENT=false` for production.
- Configure `BFF_WEBHOOK_SHARED_SECRET` on both sender and receiver.
- Set `BFF_DB_AUTO_CREATE_TABLES=false` before production go-live.
- Keep `BFF_STRICT_STARTUP_VALIDATION=true` to block weak default production credentials.
- Set `BFF_AUTO_APPLY_MIGRATIONS=false` and run migration script in release pipeline.
- Set `BFF_DEFAULT_STORE_ID` and ensure client sends `X-Store-Id` for multi-store operation.
- Configure payment provider settings (`BFF_PAYMENT_PROVIDER`, `BFF_PAYMENT_WEBHOOK_SECRET`, WeChat keys if enabled).

## 2. Infrastructure

- `docker compose -f infra/docker-compose.yml ps` shows all services healthy.
- `GET http://localhost:8080/health` returns `"status":"ok"`.
- `GET http://localhost:8080/health/ready` returns `200` continuously.
- `scripts/validate_prod_env.ps1 -EnvFile infra/.env -Strict` passes.
- `scripts/release_gate.ps1 -ExpectedEnv prod -CheckReady` passes.
- `scripts/db_migrate.ps1` runs cleanly and shows no pending migrations after deployment.
- Odoo module `drmoto_mro` is `installed`.
- `bff` database exists in PostgreSQL.

## 3. Business Readiness

- Confirm role assignment for `admin`, `manager`, `staff`, `keeper`, `cashier`.
- Validate full journey:
  - create customer
  - create work order
  - issue inventory
  - generate payment intent / record payment
  - update work order status to done
- Print all 4 document types from the document endpoint.

## 4. Data Protection

- Run backup once and verify generated files.
- Perform a restore drill in staging.
- Confirm backup retention policy (at least 7 daily snapshots).

## 5. Monitoring and Support

- Enable log collection for `bff`, `odoo`, `db`.
- Confirm on-call contact for first week of operation.
- Prepare rollback plan: previous stable compose + DB snapshot.

## 6. Final Sign-Off

- Store owner confirms process and document formats.
- Operations confirms backup/restore test passed.
- Technical lead confirms all health checks green.
- Acceptance evidence pack is exported under `infra/reports/acceptance/<timestamp>`.
