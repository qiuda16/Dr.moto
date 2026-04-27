import argparse
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def percentile(sorted_values, p):
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p) - 1))
    return sorted_values[idx]


def main():
    parser = argparse.ArgumentParser(description="Brutal stress test for DrMoto AI assistant via BFF.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change_me_now")
    parser.add_argument("--total", type=int, default=120)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=int, default=40)
    parser.add_argument("--report-dir", default="docs/recovery_reports")
    args = parser.parse_args()

    login = requests.post(
        f"{args.base_url}/auth/token",
        data={"username": args.username, "password": args.password},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    queries = [
        "现在待交付的车牌号都是多少",
        "系统里有哪些宝马车型",
        "某辆摩托车后刹异响一般先检查什么",
        "库存里有机油滤芯吗",
        "这个客户的工单现在到哪一步了",
        "帮我查下",
        "请记住客户王磊车牌京A12345，然后告诉我这个客户车牌是什么",
        "今天门店最应该先盯什么",
        "宝马F900XR保养要点有哪些",
        "报价待确认的工单有哪些",
    ]

    def one(i):
        q = random.choice(queries)
        t0 = time.time()
        try:
            resp = requests.post(
                f"{args.base_url}/ai/assistant/chat",
                json={"user_id": f"brutal-{i % 13}", "message": q, "context": {}},
                headers=headers,
                timeout=args.timeout_seconds,
            )
            cost = time.time() - t0
            payload = {}
            try:
                payload = resp.json()
            except Exception:
                pass
            return {
                "status": resp.status_code,
                "cost": cost,
                "query": q,
                "debug": payload.get("debug") or {},
                "response_preview": str(payload.get("response") or "")[:220],
            }
        except Exception as exc:
            return {"status": -1, "cost": time.time() - t0, "query": q, "error": str(exc)}

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(one, i) for i in range(max(1, args.total))]
        for future in as_completed(futures):
            rows.append(future.result())

    ok_rows = [x for x in rows if x.get("status") == 200]
    fail_rows = [x for x in rows if x.get("status") != 200]
    lat = sorted(x.get("cost", 0.0) for x in ok_rows)

    summary = {
        "total": len(rows),
        "ok": len(ok_rows),
        "fail": len(fail_rows),
        "p50": round(percentile(lat, 0.5), 3),
        "p90": round(percentile(lat, 0.9), 3),
        "p95": round(percentile(lat, 0.95), 3),
        "max": round(max(lat) if lat else 0.0, 3),
        "avg": round(statistics.mean(lat), 3) if lat else 0.0,
        "low_info_fast_path": sum(1 for x in ok_rows if x.get("debug", {}).get("low_info_fast_path")),
        "llm_overload_fallback": sum(1 for x in ok_rows if x.get("debug", {}).get("llm_overload_fallback")),
    }

    report = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": args.base_url,
        "config": {
            "total": args.total,
            "workers": args.workers,
            "timeout_seconds": args.timeout_seconds,
        },
        "summary": summary,
        "error_samples": fail_rows[:12],
    }

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"ai_brutal_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    print(f"report={out}")

    if summary["fail"] > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
