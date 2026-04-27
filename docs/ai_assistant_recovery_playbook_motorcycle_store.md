# AI Assistant Recovery Playbook (Motorcycle Store)

Updated: 2026-04-22

## Purpose
- Keep store operations running when AI model, context, or upstream service is unstable.
- Standardize recovery flow: detect -> degrade safely -> recover -> verify.

## Priority Scenarios
P0 (must recover first)
- Ready-for-delivery plate list
- Work order status and next step
- Front desk quick lookup (customer / plate / work order)

P1
- Catalog lookup by brand/model
- Repair method Q&A
- Parts and inventory lookup

P2
- Project/system explanation
- Long conversation summary

## Built-in Recovery Controls
- Deep health endpoint: `GET /health/deep`
- Recovery event stream: `GET /health/recovery-events?minutes=15`
- Forced recovery mode: `AI_RECOVERY_MODE=true`
- Automatic fallback when LLM fails (assistant still returns executable answers)
- Recovery log file: `/app/data/recovery_events.jsonl`

## One-click Recovery
Run from repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ai_assistant_recovery.ps1
```

What it does:
1. Check AI `health` and `health/deep`
2. Run scenario matrix
3. If needed, staged restart:
- `ai`
- `bff + ai`
- `redis + bff + ai`
4. Write report to `docs/recovery_reports/`

## Auto Alert Check
Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ai_recovery_alert.ps1
```

Default alert rules:
- `bff` must be `ok`
- `ollama` must be `ok`
- `memory` must be `ok`
- `recovery_mode_forced` must be `false`
- `llm_fallback_triggered` in last 15 minutes must be <= 3

If any rule fails, script exits with code `2` and writes report to:
- `infra/reports/alerts/ai_recovery_alert_*.json`

## Auto Guard (5-minute loop)
Run once to install a scheduled task:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ai_recovery_tasks.ps1 -IntervalMinutes 5
```

With webhook:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ai_recovery_tasks.ps1 -IntervalMinutes 5 -WebhookUrl "https://open.feishu.cn/..." -WebhookType feishu
```

Guard behavior each cycle:
1. Run `ai_recovery_alert.ps1`
2. If alert fails, run `ai_assistant_recovery.ps1`
3. Run alert again for post-recovery validation
4. Send webhook notification for fail/recover/critical states

## Shift Operator Steps
When users report "AI keeps failing":
1. Open `http://127.0.0.1:8001/health/deep`
2. Run `scripts/ai_recovery_alert.ps1`
3. If alert fails, run `scripts/ai_assistant_recovery.ps1`
4. Re-test these 3 questions:
- `which license plates are ready for delivery now`
- `what bmw models are in the system`
- `remember plate 京A12345 and then tell me the plate`

## Done Criteria
- `health/deep.status` is `ok` (or acceptable degraded state with no hard dependency down)
- Recovery scenario pass rate is 100%
- No sustained fallback storm in recent window
