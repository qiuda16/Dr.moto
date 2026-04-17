# Backup & Restore

## 1. Scope
Daily backups should include:

- PostgreSQL data (`odoo` + `bff` databases)
- MinIO object data
- `infra/.env` (encrypted storage only)

## 2. PostgreSQL Backup

Run from `infra/`:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
docker compose exec -T db pg_dump -U $env:POSTGRES_USER -d bff > ".\backups\bff_$ts.sql"
docker compose exec -T db pg_dump -U $env:POSTGRES_USER -d odoo > ".\backups\odoo_$ts.sql"
```

Or run the unified script from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_stack.ps1
```

## 3. MinIO Backup

Option A (volume-level snapshot):
- snapshot Docker volume `minio_data`

Option B (logical export):
- use `mc mirror` from MinIO to backup storage

## 4. Restore PostgreSQL

```powershell
Get-Content ".\backups\bff_YYYYMMDD_HHMMSS.sql" | docker compose exec -T db psql -U $env:POSTGRES_USER -d bff
Get-Content ".\backups\odoo_YYYYMMDD_HHMMSS.sql" | docker compose exec -T db psql -U $env:POSTGRES_USER -d odoo
```

Or run the unified restore script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore_stack.ps1 -BackupDir "infra/backups/YYYYMMDD_HHMMSS"
```

## 5. Restore MinIO

- Restore volume snapshot to `minio_data`, or
- mirror files back using `mc mirror --overwrite`

## 6. Recovery Drill

Run at least monthly:

1. Restore backups into a staging environment.
2. Verify:
- `/health` returns `ok`
- Odoo login works
- random order lookup and attachment access works

3. Document restore duration and failures.
