import argparse
import glob
import json
import os
import subprocess
import time
from datetime import datetime

import requests


def now_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_cmd(command, cwd):
    start = time.time()
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    output, _ = proc.communicate()
    duration = round(time.time() - start, 3)
    return {
        "command": command,
        "exit_code": proc.returncode,
        "duration_seconds": duration,
        "output": output or "",
    }


def find_latest(pattern):
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else ""


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    for enc in ["utf-8", "utf-8-sig", "gb18030"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return json.load(f)
        except Exception:
            continue
    return None


def login(base_url, username, password):
    resp = requests.post(
        "{0}/auth/token".format(base_url),
        data={"username": username, "password": password},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def run_conversation_checks(base_url, token):
    headers = {"Authorization": "Bearer {0}".format(token)}
    rows = []

    # 1) Memory recall check
    uid = "enterprise-memory-{0}".format(int(time.time()))
    pair = [
        "请记住客户王磊车牌京A12345",
        "告诉我这个客户车牌是什么",
    ]
    mem_ok = True
    mem_resp = ""
    for msg in pair:
        t0 = time.time()
        r = requests.post(
            "{0}/ai/assistant/chat".format(base_url),
            json={"user_id": uid, "message": msg, "context": {}},
            headers=headers,
            timeout=65,
        )
        payload = r.json()
        mem_resp = str(payload.get("response") or "")
        ok = r.status_code == 200 and bool(mem_resp.strip())
        if msg == pair[-1]:
            if "京A12345" not in mem_resp and "A12345" not in mem_resp:
                ok = False
        mem_ok = mem_ok and ok
        rows.append(
            {
                "check": "memory_recall",
                "message": msg,
                "ok": ok,
                "status": r.status_code,
                "cost": round(time.time() - t0, 3),
                "response_preview": mem_resp[:220],
                "debug": payload.get("debug") or {},
            }
        )

    # 2) Long multi-turn stability check
    uid2 = "enterprise-long-{0}".format(int(time.time()))
    msgs = [
        "系统里有哪些宝马车型",
        "今天门店最应该先盯什么",
        "报价待确认的工单有哪些",
        "某辆摩托车后刹异响一般先检查什么",
        "我要新建工单，需要哪些信息，先只给步骤",
        "我刚才问了什么重点，给我总结三条",
    ]
    long_ok = True
    for msg in msgs:
        t0 = time.time()
        try:
            r = requests.post(
                "{0}/ai/assistant/chat".format(base_url),
                json={"user_id": uid2, "message": msg, "context": {}},
                headers=headers,
                timeout=65,
            )
            payload = r.json()
            text = str(payload.get("response") or "").strip()
            ok = r.status_code == 200 and bool(text)
            if "�" in text:
                ok = False
            long_ok = long_ok and ok
            rows.append(
                {
                    "check": "long_conversation",
                    "message": msg,
                    "ok": ok,
                    "status": r.status_code,
                    "cost": round(time.time() - t0, 3),
                    "response_preview": text[:220],
                    "debug": payload.get("debug") or {},
                }
            )
        except Exception as exc:
            long_ok = False
            rows.append(
                {
                    "check": "long_conversation",
                    "message": msg,
                    "ok": False,
                    "status": -1,
                    "cost": round(time.time() - t0, 3),
                    "error": str(exc),
                }
            )

    return {
        "checks": rows,
        "summary": {
            "memory_recall_ok": mem_ok,
            "long_conversation_ok": long_ok,
            "total_checks": len(rows),
            "passed": sum(1 for row in rows if row.get("ok")),
            "failed": sum(1 for row in rows if not row.get("ok")),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Enterprise brutal suite for AI assistant.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change_me_now")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--report-dir", default="docs/recovery_reports")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    report_dir = os.path.join(workspace, args.report_dir)
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    stages = []

    # Stage 0: smoke health
    stages.append(
        run_cmd(
            'powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-RestMethod -Method Get -Uri {0}/health -TimeoutSec 20 | ConvertTo-Json -Depth 5"'.format(
                args.base_url
            ),
            workspace,
        )
    )

    # Stage 1: quality regression (core)
    stages.append(
        run_cmd(
            "python scripts/ai_quality_eval.py --base-url {0} --rounds 20 --timeout-seconds 65".format(args.base_url),
            workspace,
        )
    )
    quality_report = find_latest(os.path.join(report_dir, "ai_quality_eval_*.json"))

    # Stage 2: loop test (realistic concurrency)
    stages.append(
        run_cmd(
            "python scripts/ai_customer_loop_test.py --base-url {0} --rounds 8 --workers 8 --timeout-seconds 50".format(
                args.base_url
            ),
            workspace,
        )
    )
    loop_report_8 = find_latest(os.path.join(report_dir, "ai_customer_loop_test_*.json"))

    # Stage 3: loop test (brutal concurrency)
    stages.append(
        run_cmd(
            "python scripts/ai_customer_loop_test.py --base-url {0} --rounds 8 --workers 24 --timeout-seconds 50".format(
                args.base_url
            ),
            workspace,
        )
    )
    loop_report_24 = find_latest(os.path.join(report_dir, "ai_customer_loop_test_*.json"))

    # Stage 4: raw brutal test
    stages.append(
        run_cmd(
            "python scripts/ai_brutal_test.py --base-url {0} --total 400 --workers 40 --timeout-seconds 50".format(
                args.base_url
            ),
            workspace,
        )
    )
    brutal_report = find_latest(os.path.join(report_dir, "ai_brutal_test_*.json"))

    # Stage 5: chaos and recovery
    stages.append(
        run_cmd(
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ai_chaos_test.ps1",
            workspace,
        )
    )
    chaos_report = find_latest(os.path.join(report_dir, "ai_chaos_test_*.json"))

    # Stage 6: direct conversation checks
    conv = None
    try:
        token = login(args.base_url, args.username, args.password)
        conv = run_conversation_checks(args.base_url, token)
    except Exception as exc:
        conv = {"error": str(exc), "summary": {"memory_recall_ok": False, "long_conversation_ok": False}}

    quality_obj = load_json(quality_report)
    loop8_obj = load_json(loop_report_8)
    loop24_obj = load_json(loop_report_24)
    brutal_obj = load_json(brutal_report)
    chaos_obj = load_json(chaos_report)

    chaos_stage_ok = bool(stages[6]["exit_code"] == 0) if len(stages) > 6 else False
    chaos_summary_pass = bool((chaos_obj or {}).get("summary", {}).get("fail", 1) == 0)
    gate = {
        "quality_pass_rate_ge_95": bool((quality_obj or {}).get("summary", {}).get("quality_pass_rate", 0) >= 95),
        "loop8_zero_fail": bool((loop8_obj or {}).get("summary", {}).get("turn_fail", 1) == 0),
        "loop24_zero_fail": bool((loop24_obj or {}).get("summary", {}).get("turn_fail", 1) == 0),
        "brutal_zero_fail": bool((brutal_obj or {}).get("summary", {}).get("fail", 1) == 0),
        "chaos_pass": bool(chaos_summary_pass or chaos_stage_ok),
        "memory_recall_pass": bool((conv or {}).get("summary", {}).get("memory_recall_ok")),
        "long_conversation_pass": bool((conv or {}).get("summary", {}).get("long_conversation_ok")),
    }
    gate["overall_pass"] = all(gate.values())

    out = {
        "time": datetime.now().isoformat(),
        "config": {
            "base_url": args.base_url,
            "workspace": workspace,
        },
        "stages": stages,
        "reports": {
            "quality_report": quality_report,
            "loop_report_8": loop_report_8,
            "loop_report_24": loop_report_24,
            "brutal_report": brutal_report,
            "chaos_report": chaos_report,
        },
        "conversation_checks": conv,
        "gate": gate,
        "snapshots": {
            "quality_summary": (quality_obj or {}).get("summary"),
            "loop8_summary": (loop8_obj or {}).get("summary"),
            "loop24_summary": (loop24_obj or {}).get("summary"),
            "brutal_summary": (brutal_obj or {}).get("summary"),
            "chaos_summary": (chaos_obj or {}).get("summary"),
        },
    }

    report_path = os.path.join(report_dir, "ai_enterprise_brutal_suite_{0}.json".format(now_ts()))
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(report_dir, "ai_enterprise_brutal_suite_{0}.md".format(now_ts()))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# AI Enterprise Brutal Suite\n\n")
        f.write("- Overall Pass: **{0}**\n".format(out["gate"]["overall_pass"]))
        f.write("- Quality Pass Rate >=95%: {0}\n".format(out["gate"]["quality_pass_rate_ge_95"]))
        f.write("- Loop(8 workers) Zero Fail: {0}\n".format(out["gate"]["loop8_zero_fail"]))
        f.write("- Loop(24 workers) Zero Fail: {0}\n".format(out["gate"]["loop24_zero_fail"]))
        f.write("- Brutal Zero Fail: {0}\n".format(out["gate"]["brutal_zero_fail"]))
        f.write("- Chaos Pass: {0}\n".format(out["gate"]["chaos_pass"]))
        f.write("- Memory Recall Pass: {0}\n".format(out["gate"]["memory_recall_pass"]))
        f.write("- Long Conversation Pass: {0}\n".format(out["gate"]["long_conversation_pass"]))
        f.write("\n## Reports\n")
        for key, value in out["reports"].items():
            f.write("- {0}: `{1}`\n".format(key, value))

    print(json.dumps({"gate": gate, "report": report_path}, ensure_ascii=False))
    print("report={0}".format(report_path))
    print("report_md={0}".format(md_path))

    if not gate["overall_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
