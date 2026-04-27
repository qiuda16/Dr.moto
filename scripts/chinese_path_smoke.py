#!/usr/bin/env python3
"""Smoke test for Chinese path/file I/O reliability on the host runtime."""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    base_dir = repo_root / "infra" / "reports" / "runtime_smoke" / "中文路径测试"
    file_path = base_dir / "维修手册_机油扭矩_示例.json"
    now = datetime.now().isoformat(timespec="seconds")
    payload = {
        "name": "机车博士",
        "scenario": "中文路径和中文内容读写",
        "timestamp": now,
        "notes": [
            "换机油",
            "换机滤",
            "扭矩按手册标准执行",
        ],
    }

    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    roundtrip = json.loads(file_path.read_text(encoding="utf-8"))
    if roundtrip != payload:
        print("[chinese-path-smoke] roundtrip payload mismatch", file=sys.stderr)
        return 1

    files = [p.name for p in base_dir.iterdir() if p.is_file()]
    if file_path.name not in files:
        print("[chinese-path-smoke] expected file not found via directory listing", file=sys.stderr)
        return 1

    print("[chinese-path-smoke] passed")
    print(f"[chinese-path-smoke] file={file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
