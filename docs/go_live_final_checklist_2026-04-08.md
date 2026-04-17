# Go-Live Final Checklist

Date: 2026-04-08
Owner: Codex

## 1. Service Status

- [ ] `infra-bff-1` healthy
- [ ] `infra-ai-1` running
- [ ] `infra-odoo-1` healthy
- [ ] `infra-db-1` healthy
- [ ] `infra-redis-1` healthy
- [ ] `infra-minio-1` running
- [ ] `infra-ocr_vl-1` running

## 2. Core Functional Checks

- [ ] Admin login works
- [ ] Dashboard summary loads
- [ ] Work-order list page loads
- [ ] Customer creation works
- [ ] Work-order creation works
- [ ] Work-order document render works
- [ ] Quote create and publish work
- [ ] AI assistant query works
- [ ] AI assistant write action works

## 3. Frontend Build Checks

- [ ] `clients/cs_workspace` build passes
- [ ] `clients/web_staff` build passes
- [ ] `clients/web_display` build passes
- [ ] `clients/mp_customer` build passes
- [ ] `clients/mp_staff` build passes
- [ ] `clients/mp_customer_uni` build passes

## 4. AI Readiness

- [ ] Main model is `qwen3:8b`
- [ ] Context window is `40960`
- [ ] Catalog query returns real records
- [ ] AI write receipts are visible in chat UI
- [ ] Memory recall fast path works for short-term facts
- [ ] Vehicle / customer / work-order follow-up queries still resolve correctly

## 5. Data Safety

- [ ] BFF health is `ok`
- [ ] DB is reachable
- [ ] Odoo is reachable
- [ ] Redis is reachable
- [ ] No unresolved 500 errors in latest smoke tests
- [ ] Write actions remain limited to approved business scope

## 6. Performance / Stability

- [ ] Sequential smoke loop passes
- [ ] Concurrent mixed-load test passes
- [ ] AI remains responsive after concurrent test
- [ ] Services remain healthy after test

## 7. Known Non-Blocking Risks

- [ ] Large frontend bundle warnings acknowledged
- [ ] Sass deprecation warnings acknowledged
- [ ] `npm audit` moderate findings for `web_display` acknowledged
- [ ] AI long-session latency and memory limitations acknowledged

## 8. Rollback Readiness

- [ ] `infra/docker-compose.yml` startup path confirmed
- [ ] Backup / restore scripts are available under `scripts/`
- [ ] Operator knows service URLs
- [ ] Operator knows how to restart `ai` and `bff`

## 9. Recommended Operator Commands

```powershell
docker compose -f infra\docker-compose.yml ps
docker compose -f infra\docker-compose.yml up -d --build bff
docker compose -f infra\docker-compose.yml up -d --build ai
powershell -ExecutionPolicy Bypass -File scripts\smoke_test.ps1 -BaseUrl http://127.0.0.1:18080
```

## 10. Final Decision

- [ ] Ready for controlled go-live
- [ ] Hold release and continue hardening
