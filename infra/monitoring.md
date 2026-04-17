# Monitoring

## 1. Minimum Signals

Track these before going live:

- BFF `/health` status
- Odoo availability (`/web`)
- DB connection health
- Redis connection health
- API error rate (4xx/5xx split)
- P95 request latency
- Prometheus metrics endpoint (`/metrics` by default)

## 1.1 Metrics Endpoint

- URL: `GET /metrics`
- Controlled by env:
  - `BFF_ENABLE_METRICS=true|false`
  - `BFF_METRICS_PATH=/metrics`

Key metrics:

- `drmoto_http_requests_total`
- `drmoto_http_request_duration_seconds`
- `drmoto_http_in_progress`
- `drmoto_app_info`

## 2. Log Collection

Start with Docker logs:

```powershell
docker compose logs -f bff
docker compose logs -f odoo
docker compose logs -f db
```

For production, ship logs to a centralized platform (ELK/Loki/Cloud logging).

## 3. Alert Baseline

Create alerts for:

- `health.status != ok` for 5 minutes
- `5xx error rate > 2%` over 10 minutes
- `p95 request latency > 1.5s` over 10 minutes
- `in-flight requests > 100` for 5 minutes
- DB restart events
- Disk usage > 80% on data volume

## 4. KPI Dashboards (Operational)

- Active work orders
- Orders created today
- Orders completed today
- Quote publish count
- Inventory issue count

## 5. Weekly Review

Every week:

1. Review top 5 API errors
2. Review slowest 5 endpoints
3. Validate backup completeness
4. Run `scripts/alert_check.ps1` and archive output
5. Run `scripts/failure_drill.ps1` in maintenance window and record recovery time

Alert check reports are saved by default to `infra/reports/alerts/` as JSON for audit trail.
