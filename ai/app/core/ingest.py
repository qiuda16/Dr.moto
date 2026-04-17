import json
import os
from pathlib import Path

from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _collection_path(collection_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (collection_name or "manuals"))
    return DATA_DIR / f"{safe_name}.json"


def ingest_pdf(file_path: str, collection_name: str = "manuals"):
    reader = PdfReader(file_path)
    records = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        records.append(
            {
                "page": page_number,
                "page_content": text[:12000],
            }
        )

    target = _collection_path(collection_name)
    target.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(records)


def ingest_records(records: list[dict], collection_name: str = "manuals"):
    normalized = []
    for item in records or []:
        content = (item.get("page_content") or item.get("text") or "").strip()
        if not content:
            continue
        normalized.append(
            {
                "page": item.get("page") or item.get("page_number") or len(normalized) + 1,
                "page_content": content[:12000],
                "summary": item.get("summary"),
                "specs": item.get("specs") or [],
                "procedures": item.get("procedures") or [],
            }
        )
    target = _collection_path(collection_name)
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(normalized)


def clear_db():
    for file in DATA_DIR.glob("*.json"):
        try:
            file.unlink()
        except OSError:
            pass
