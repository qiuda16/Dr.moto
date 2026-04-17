# DB Migration Guide (BFF)

Updated: 2026-03-29

## 1. Purpose

Use versioned SQL migrations for schema changes in production, instead of relying on runtime `create_all`.

## 2. Location

- SQL files: `bff/migrations/versions/*.sql`
- Rollback templates: `bff/migrations/rollback_templates/*.sql`
- Runner module: `bff/app/core/migrations.py`
- Ops script: `scripts/db_migrate.ps1`

## 3. How to run

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/db_migrate.ps1
```

The runner creates `schema_migrations` table (if missing), executes pending SQL files in lexical order, and records applied versions.

## 4. Release process

1. Add new SQL file with increasing prefix (for example `0002_add_xxx.sql`).
2. Apply in staging and verify tests + smoke.
3. Apply in production before application rollout.
4. Keep `BFF_AUTO_APPLY_MIGRATIONS=false` in production for controlled release.

## 5. Safety notes

- Write idempotent SQL whenever possible (`IF NOT EXISTS`).
- For destructive changes, prepare rollback SQL and tested backup restore plan.
- For each production migration, add a same-version rollback template (for example `0004_xxx_rollback.sql`).
