# Infra Runbook

## 1. Goal
Bring up a stable store-operation stack for daily usage:

- Odoo core business
- BFF API gateway
- Redis
- PostgreSQL
- MinIO

## 2. Pre-Start Checklist

1. Copy `infra/.env.example` to `infra/.env`.
2. Replace all default passwords in `infra/.env`.
3. Set `BFF_ENV=prod`.
4. Set `BFF_ENABLE_DEV_ENDPOINTS=false`.
5. Set `BFF_ENABLE_MOCK_PAYMENT=false` unless doing internal demo.
6. Set `BFF_WEBHOOK_SHARED_SECRET` and configure the same value in Odoo callback sender.
7. Review login rate-limit settings (`BFF_LOGIN_RATE_LIMIT_MAX_ATTEMPTS`, `BFF_LOGIN_RATE_LIMIT_WINDOW_SECONDS`).
8. Set `BFF_DB_AUTO_CREATE_TABLES=false` in production and use migration-based schema changes.
9. Tune DB pool settings by load (`BFF_DB_POOL_SIZE`, `BFF_DB_MAX_OVERFLOW`, `BFF_DB_POOL_TIMEOUT_SECONDS`).
10. Confirm Odoo retry/timeout policy (`BFF_ODOO_TIMEOUT_SECONDS`, `BFF_ODOO_RETRY_MAX_ATTEMPTS`, `BFF_ODOO_RETRY_BACKOFF_SECONDS`).
11. Keep `BFF_STRICT_STARTUP_VALIDATION=true` so weak/default production secrets fail fast at startup.
12. Keep `BFF_AUTO_APPLY_MIGRATIONS=false` for production and run migrations explicitly before deployment.
13. Keep `BFF_LOG_FORMAT=json` to support centralized log ingestion and querying.
14. For multi-store operations, configure `BFF_DEFAULT_STORE_ID` and ensure clients send `X-Store-Id`.
15. Configure payment mode and callback signature (`BFF_PAYMENT_PROVIDER`, `BFF_PAYMENT_WEBHOOK_SECRET`).

## 3. Start Services

From `infra/`:

```powershell
docker compose up -d --build
```

Check service status:

```powershell
docker compose ps
```

## 4. Validate System Health

1. Open Odoo: `http://localhost:8069`
2. Check BFF health:

```powershell
curl http://localhost:8080/health
```

Expected:
- `"status": "ok"` means all dependencies healthy
- `"status": "degraded"` means DB or Odoo connection issue

Run DB migrations before first production start or any schema release:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/db_migrate.ps1
```

Or run the full release gate pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release_gate.ps1 -AdminPassword "<your_admin_password>" -StoreId "default"
```

Run alert threshold check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/alert_check.ps1
```

Run quarterly failure drill (maintenance window):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/failure_drill.ps1 -FailureDurationSeconds 20
```

If rollback is required:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rollback_release.ps1 -BackupDir "infra/backups/YYYYMMDD_HHMMSS" -AdminPassword "<your_admin_password>" -StoreId "default"
```

## 5. Login Credentials (BFF)

Token endpoint:

```http
POST /auth/token
```

Use:
- username: `BFF_ADMIN_USERNAME`
- password: `BFF_ADMIN_PASSWORD` (or the password for `BFF_ADMIN_PASSWORD_HASH`)

## 6. Daily Operations

- Restart only one service:
```powershell
docker compose restart bff
```

- Tail logs:
```powershell
docker compose logs -f bff
docker compose logs -f odoo
```

- Stop stack:
```powershell
docker compose down
```

## 7. Incident Quick Actions

### BFF unhealthy
1. `docker compose logs --tail=200 bff`
2. verify `.env` secrets and Odoo credentials
3. restart `bff` then `odoo`

### Odoo unavailable
1. `docker compose logs --tail=200 odoo`
2. `docker compose logs --tail=200 db`
3. verify DB credentials match `.env`

### MinIO upload failure
1. `docker compose logs --tail=200 minio`
2. check `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`

## 8. Production Guardrails

- Never expose `BFF_ENABLE_DEV_ENDPOINTS=true` in production.
- Keep admin password rotated and stored securely.
- Perform backup daily (see `backup_restore.md`).
- Keep TLS and reverse proxy in front of public endpoints.

## 9. Recommended Day-1 Commands

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/preflight_prod.ps1
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
```
