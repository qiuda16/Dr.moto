import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List

import requests


TEST_CASES = [
    {"name": "catalog_cn", "message": "系统里有哪些宝马车型"},
    {"name": "catalog_en", "message": "what bmw models are in the system"},
    {"name": "workorder_status", "message": "这个客户的工单现在到哪一步了"},
    {"name": "delivery_plates", "message": "现在带交付的车牌号都是多少"},
    {"name": "ops_focus", "message": "今天门店最应该先盯什么"},
    {"name": "repair_brake_noise", "message": "某辆摩托车后刹异响一般先检查什么"},
    {"name": "repair_maintenance", "message": "摩托车保养一般包括哪些项目"},
    {"name": "write_guidance_workorder", "message": "我要新建工单，需要哪些信息，先只给步骤"},
    {"name": "write_guidance_quote", "message": "我要生成报价草稿，先告诉我你会写入什么字段"},
    {"name": "low_info", "message": "帮我查下"},
]


def login(base_url: str, username: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/auth/token",
        data={"username": username, "password": password},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def has_garbled_text(text: str) -> bool:
    markers = ["锛", "鏈€", "鈥", "闂", "鍚", "璇", "鈹", "�"]
    return sum(text.count(m) for m in markers) >= 3


def evaluate_one(case_name: str, message: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response_text = str(payload.get("response") or "").strip()
    debug = payload.get("debug") or {}
    issues: List[str] = []

    if not response_text:
        issues.append("empty_response")
    if has_garbled_text(response_text):
        issues.append("garbled_text")
    if re.search(r"联系.*(技术支持|团队|部门)", response_text):
        issues.append("escalation_tone")
    if "当前系统字段不可读" in response_text or "待补录" in response_text:
        issues.append("template_placeholder")

    if case_name in {"repair_brake_noise", "repair_maintenance"}:
        if not any(token in response_text for token in ["1.", "2.", "先", "检查"]):
            issues.append("repair_not_actionable")
    if case_name.startswith("write_guidance"):
        if not any(token in response_text for token in ["步骤", "字段", "信息", "先不", "确认"]):
            issues.append("write_guidance_weak")
        if debug.get("write_executed"):
            issues.append("unexpected_write_execution")
    if case_name == "workorder_status":
        if not any(token in response_text for token in ["工单", "状态", "车牌", "客户名", "工单号"]):
            issues.append("status_answer_unfocused")
    if case_name == "low_info":
        if not any(token in response_text for token in ["客户名", "车牌", "工单号", "关键信息"]):
            issues.append("low_info_not_guided")

    return {
        "case": case_name,
        "ok": len(issues) == 0,
        "issues": issues,
        "response_preview": response_text[:260],
        "debug": debug,
    }


def main():
    parser = argparse.ArgumentParser(description="Quality-focused eval for AI assistant answers.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change_me_now")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=65)
    parser.add_argument("--report-dir", default="docs/recovery_reports")
    args = parser.parse_args()

    token = login(args.base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    rows = []
    for round_idx in range(max(1, args.rounds)):
        for i, case in enumerate(TEST_CASES):
            user_id = f"quality-{round_idx}-{i}"
            start = time.time()
            try:
                resp = requests.post(
                    f"{args.base_url}/ai/assistant/chat",
                    json={"user_id": user_id, "message": case["message"], "context": {}},
                    headers=headers,
                    timeout=args.timeout_seconds,
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                result = evaluate_one(case["name"], case["message"], payload if isinstance(payload, dict) else {})
                result.update(
                    {
                        "round": round_idx,
                        "status": resp.status_code,
                        "cost": round(time.time() - start, 3),
                        "message": case["message"],
                    }
                )
                if resp.status_code != 200:
                    result["ok"] = False
                    result["issues"].append("http_not_200")
                rows.append(result)
            except Exception as exc:
                rows.append(
                    {
                        "round": round_idx,
                        "case": case["name"],
                        "status": -1,
                        "cost": round(time.time() - start, 3),
                        "message": case["message"],
                        "ok": False,
                        "issues": ["request_exception"],
                        "error": str(exc),
                    }
                )

    ok_rows = [row for row in rows if row.get("ok")]
    fail_rows = [row for row in rows if not row.get("ok")]
    issue_counter: Dict[str, int] = {}
    for row in fail_rows:
        for issue in row.get("issues") or []:
            issue_counter[issue] = issue_counter.get(issue, 0) + 1

    summary = {
        "total": len(rows),
        "ok": len(ok_rows),
        "fail": len(fail_rows),
        "quality_pass_rate": round((len(ok_rows) / len(rows) * 100.0), 2) if rows else 0.0,
        "avg_cost": round(sum(row.get("cost", 0.0) for row in rows) / len(rows), 3) if rows else 0.0,
        "issue_counter": issue_counter,
    }

    report = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "base_url": args.base_url,
            "rounds": args.rounds,
            "case_count": len(TEST_CASES),
            "timeout_seconds": args.timeout_seconds,
        },
        "summary": summary,
        "fail_samples": fail_rows[:40],
    }

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"ai_quality_eval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    print(f"report={out}")

    if summary["fail"] > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
