#!/usr/bin/env python3
"""Scan tracked source files for potential secret leaks."""

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

ALLOWLIST_SUBSTRINGS = (
    "your-secret-key-change-me-in-production",
    "set OPENAI_API_KEY=your_api_key_here",
    "OPENAI_API_KEY=${OPENAI_API_KEY}",
    "AI_OCR_LLM_API_KEY",
)

PATTERNS = [
    ("openai_sk", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("openai_api_key_literal", re.compile(r'OPENAI_API_KEY["\']?\s*[:=]\s*["\'][^"\']{16,}["\']')),
    ("generic_api_key_literal", re.compile(r'API_KEY["\']?\s*[:=]\s*["\'][^"\']{16,}["\']')),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]


def iter_tracked_files(repo_root: Path) -> list[Path]:
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=repo_root, check=True, capture_output=True)
    files: list[Path] = []
    for item in [x for x in proc.stdout.split(b"\x00") if x]:
        rel = item.decode("utf-8", errors="replace")
        if rel.startswith(SKIP_PREFIXES):
            continue
        p = Path(rel)
        if p.suffix.lower() in TEXT_EXTENSIONS:
            files.append(repo_root / p)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report_dir = Path(args.report_dir).resolve() if args.report_dir else repo_root / "infra" / "reports" / "secret_scan"
    report_dir.mkdir(parents=True, exist_ok=True)

    issues: list[dict] = []
    scanned = 0
    for path in iter_tracked_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        scanned += 1
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(allow in line for allow in ALLOWLIST_SUBSTRINGS):
                continue
            for issue_type, pattern in PATTERNS:
                if pattern.search(line):
                    issues.append(
                        {
                            "file": rel,
                            "line": line_no,
                            "type": issue_type,
                            "snippet": line[:200],
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

    print(f"[secret-scan] scanned={scanned} issues={len(issues)}")
    print(f"[secret-scan] report={report_path}")
    if issues:
        for issue in issues[:20]:
            print(f" - {issue['file']}:{issue['line']} :: {issue['type']}")
        if len(issues) > 20:
            print(f" - ... {len(issues) - 20} more")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
