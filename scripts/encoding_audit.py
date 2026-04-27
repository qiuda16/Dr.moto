#!/usr/bin/env python3
"""Audit tracked source files for UTF-8 and common mojibake indicators."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".vue",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".txt",
    ".html",
    ".css",
    ".scss",
    ".env",
}

SKIP_PREFIXES = (
    ".git/",
    "node_modules/",
    "clients/web_staff/node_modules/",
    "clients/web_staff/dist/",
    "coverage/",
)

QUESTION_RUN = re.compile(r"\?{4,}")


def list_tracked_files(repo_root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    raw_items = [item for item in proc.stdout.split(b"\x00") if item]
    paths: list[Path] = []
    for item in raw_items:
        rel = item.decode("utf-8", errors="replace")
        if rel.startswith(SKIP_PREFIXES):
            continue
        p = Path(rel)
        if p.suffix.lower() in TEXT_EXTENSIONS:
            paths.append(repo_root / p)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report_dir = (
        Path(args.report_dir).resolve()
        if args.report_dir
        else repo_root / "infra" / "reports" / "encoding_audit"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    issues: list[dict] = []
    scanned = 0
    for path in list_tracked_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        try:
            raw = path.read_bytes()
        except OSError as exc:
            issues.append({"file": rel, "type": "read_error", "detail": str(exc)})
            continue
        if b"\x00" in raw:
            continue
        scanned += 1
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(
                {
                    "file": rel,
                    "type": "utf8_decode_error",
                    "detail": f"byte={exc.start}",
                }
            )
            continue

        if "\ufffd" in text:
            issues.append({"file": rel, "type": "replacement_char_found", "detail": "contains U+FFFD"})

        for match in QUESTION_RUN.finditer(text):
            issues.append(
                {
                    "file": rel,
                    "type": "question_run_found",
                    "detail": f"index={match.start()} length={len(match.group(0))}",
                }
            )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(repo_root),
        "scanned_files": scanned,
        "issue_count": len(issues),
        "issues": issues,
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"{ts}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[encoding-audit] scanned={scanned} issues={len(issues)}")
    print(f"[encoding-audit] report={report_path}")
    if issues:
        for issue in issues[:20]:
            print(f" - {issue['file']} :: {issue['type']} ({issue['detail']})")
        if len(issues) > 20:
            print(f" - ... {len(issues) - 20} more")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
