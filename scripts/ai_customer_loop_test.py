import argparse
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import requests


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str
    turns: List[str]


SCENARIOS = [
    Scenario("sales_brand_catalog", "sales", ["系统里有哪些宝马车型"]),
    Scenario("sales_brand_catalog_en", "sales", ["what bmw models are in the system"]),
    Scenario("sales_stock_plate", "sales", ["现在带交付的车牌号都是多少"]),
    Scenario("sales_customer_stage", "sales", ["这个客户的工单现在到哪一步了"]),
    Scenario("sales_today_focus", "sales", ["今天门店最应该先盯什么"]),
    Scenario("service_brake_noise", "service", ["某辆摩托车后刹异响一般先检查什么"]),
    Scenario("service_oil_filter", "service", ["库存里有机油滤芯吗"]),
    Scenario("service_quote_pending", "service", ["报价待确认的工单有哪些"]),
    Scenario("service_overdue", "service", ["超期工单有哪些，优先处理顺序是什么"]),
    Scenario("service_delivery_ready", "service", ["待交付车辆有哪些"]),
    Scenario("crm_followup", "crm", ["请记住客户王磊车牌京A12345", "告诉我这个客户车牌是什么"]),
    Scenario("crm_recent_orders", "crm", ["这个客户还有哪些工单"]),
    Scenario("ops_dashboard", "ops", ["门店总览里待施工、施工中、待交付分别多少"]),
    Scenario("ops_priority", "ops", ["今天先盯什么，给我3条建议"]),
    Scenario("ops_progress", "ops", ["施工中优先关注哪些车牌"]),
    Scenario("low_info_cn", "robustness", ["帮我查下"]),
    Scenario("low_info_en", "robustness", ["help me check"]),
    Scenario("ambiguous_query", "robustness", ["看看"]),
    Scenario("write_intent_customer", "write_intent", ["我想新增客户，需要提供哪些字段，先不要实际创建"]),
    Scenario("write_intent_workorder", "write_intent", ["我要新建工单，需要哪些信息，先只给步骤"]),
    Scenario("write_intent_quote", "write_intent", ["我要生成报价草稿，先告诉我你会写入什么字段"]),
    Scenario("write_intent_status", "write_intent", ["如果要修改工单状态为待交付，应该怎么做"]),
    Scenario("knowledge_general", "knowledge", ["摩托车保养一般包括哪些项目"]),
    Scenario("knowledge_specific", "knowledge", ["宝马F900XR保养要点有哪些"]),
    Scenario("knowledge_safety", "knowledge", ["更换刹车片前要先检查什么安全项"]),
]


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    idx = min(len(values) - 1, max(0, int(len(values) * p) - 1))
    return values[idx]


def login(base_url: str, username: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/auth/token",
        data={"username": username, "password": password},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def run_one_scenario(
    base_url: str,
    headers: Dict[str, str],
    scenario: Scenario,
    session_user_id: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    turn_rows = []
    all_ok = True
    for turn_idx, message in enumerate(scenario.turns):
        start = time.time()
        item = {
            "turn_index": turn_idx,
            "message": message,
        }
        try:
            response = requests.post(
                f"{base_url}/ai/assistant/chat",
                json={"user_id": session_user_id, "message": message, "context": {}},
                headers=headers,
                timeout=timeout_seconds,
            )
            cost = time.time() - start
            payload = {}
            try:
                payload = response.json()
            except Exception:
                payload = {}
            ok = response.status_code == 200 and bool((payload.get("response") or "").strip())
            all_ok = all_ok and ok
            item.update(
                {
                    "status": response.status_code,
                    "ok": ok,
                    "cost": cost,
                    "response_preview": str(payload.get("response") or "")[:220],
                    "debug": payload.get("debug") or {},
                }
            )
        except Exception as exc:
            all_ok = False
            item.update(
                {
                    "status": -1,
                    "ok": False,
                    "cost": time.time() - start,
                    "error": str(exc),
                }
            )
        turn_rows.append(item)

    return {
        "scenario": scenario.name,
        "category": scenario.category,
        "session_user_id": session_user_id,
        "ok": all_ok,
        "turns": turn_rows,
    }


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_turns = [turn for row in rows for turn in row.get("turns", [])]
    ok_turns = [turn for turn in all_turns if turn.get("ok")]
    fail_turns = [turn for turn in all_turns if not turn.get("ok")]
    latencies = sorted(turn.get("cost", 0.0) for turn in ok_turns)

    category_summary = {}
    proxy_reason_counter = {}
    for category in sorted(set(row.get("category") for row in rows)):
        cat_rows = [row for row in rows if row.get("category") == category]
        cat_turns = [turn for row in cat_rows for turn in row.get("turns", [])]
        cat_ok_turns = [turn for turn in cat_turns if turn.get("ok")]
        cat_lat = sorted(turn.get("cost", 0.0) for turn in cat_ok_turns)
        category_summary[category] = {
            "sessions": len(cat_rows),
            "session_ok": sum(1 for row in cat_rows if row.get("ok")),
            "turn_total": len(cat_turns),
            "turn_ok": len(cat_ok_turns),
            "turn_fail": len(cat_turns) - len(cat_ok_turns),
            "p95": round(percentile(cat_lat, 0.95), 3),
        }

    for turn in ok_turns:
        debug = turn.get("debug") or {}
        if debug.get("proxy_fallback"):
            reason = str(debug.get("reason") or "unknown")
            proxy_reason_counter[reason] = proxy_reason_counter.get(reason, 0) + 1

    return {
        "sessions_total": len(rows),
        "sessions_ok": sum(1 for row in rows if row.get("ok")),
        "sessions_fail": sum(1 for row in rows if not row.get("ok")),
        "turn_total": len(all_turns),
        "turn_ok": len(ok_turns),
        "turn_fail": len(fail_turns),
        "p50": round(percentile(latencies, 0.5), 3),
        "p90": round(percentile(latencies, 0.9), 3),
        "p95": round(percentile(latencies, 0.95), 3),
        "max": round(max(latencies) if latencies else 0.0, 3),
        "avg": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "proxy_fallback": sum(1 for turn in ok_turns if (turn.get("debug") or {}).get("proxy_fallback")),
        "low_info_fast_path": sum(1 for turn in ok_turns if (turn.get("debug") or {}).get("low_info_fast_path")),
        "global_query_fast_path": sum(1 for turn in ok_turns if (turn.get("debug") or {}).get("global_query_fast_path")),
        "store_ops_fast_path": sum(1 for turn in ok_turns if (turn.get("debug") or {}).get("store_ops_fast_path")),
        "write_command_fast_path": sum(1 for turn in ok_turns if (turn.get("debug") or {}).get("write_command_fast_path")),
        "proxy_reason_counter": proxy_reason_counter,
        "category_summary": category_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Loop test for customer-service scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change_me_now")
    parser.add_argument("--rounds", type=int, default=20, help="How many full passes over scenario set.")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=int, default=35)
    parser.add_argument("--seed", type=int, default=20260423)
    parser.add_argument("--report-dir", default="docs/recovery_reports")
    args = parser.parse_args()

    random.seed(args.seed)
    token = login(args.base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    runs = []
    user_counter = 0
    for round_idx in range(max(1, args.rounds)):
        shuffled = list(SCENARIOS)
        random.shuffle(shuffled)
        for scenario in shuffled:
            runs.append((round_idx, scenario, f"loop-{round_idx}-{user_counter}"))
            user_counter += 1

    rows = []

    def _job(item):
        round_idx, scenario, session_user_id = item
        result = run_one_scenario(
            base_url=args.base_url,
            headers=headers,
            scenario=scenario,
            session_user_id=session_user_id,
            timeout_seconds=args.timeout_seconds,
        )
        result["round"] = round_idx
        return result

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(_job, item) for item in runs]
        for future in as_completed(futures):
            rows.append(future.result())

    summary = summarize(rows)
    fail_samples = []
    for row in rows:
        if row.get("ok"):
            continue
        fail_turns = [turn for turn in row.get("turns", []) if not turn.get("ok")]
        fail_samples.append(
            {
                "scenario": row.get("scenario"),
                "category": row.get("category"),
                "session_user_id": row.get("session_user_id"),
                "fails": fail_turns[:3],
            }
        )
        if len(fail_samples) >= 25:
            break

    report = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": args.base_url,
        "config": {
            "rounds": args.rounds,
            "workers": args.workers,
            "timeout_seconds": args.timeout_seconds,
            "scenario_count": len(SCENARIOS),
            "seed": args.seed,
        },
        "summary": summary,
        "fail_samples": fail_samples,
    }

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"ai_customer_loop_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    print(f"report={out}")

    if summary["turn_fail"] > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
