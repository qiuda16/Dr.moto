import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"


def _collection_path(collection_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (collection_name or "manuals"))
    return DATA_DIR / f"{safe_name}.json"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_text(value: Any) -> str:
    return _clean_text(value).lower()


def _tokenize(text: str) -> List[str]:
    return [token for token in re.split(r"[^0-9A-Za-z\u4e00-\u9fa5]+", _normalize_text(text)) if token]


def _iter_manual_payloads(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    if not isinstance(item, dict):
        return payloads
    payloads.append(item)
    raw = item.get("raw_result_json")
    if isinstance(raw, dict):
        payloads.append(raw)
        normalized = raw.get("normalized_manual")
        if isinstance(normalized, dict):
            payloads.append(normalized)
    normalized = item.get("normalized_manual")
    if isinstance(normalized, dict):
        payloads.append(normalized)
    return payloads


def _flatten_record_text(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ["title", "file_name", "category", "page_content", "document_title", "doc_type"]:
        value = _clean_text(item.get(key))
        if value:
            parts.append(value)

    for payload in _iter_manual_payloads(item):
        for key in ["title", "summary", "overview", "scope", "vehicle_model", "model", "system"]:
            value = _clean_text(payload.get(key))
            if value:
                parts.append(value)

        for spec in payload.get("specs") or []:
            if isinstance(spec, dict):
                parts.append(
                    " ".join(
                        part
                        for part in [
                            _clean_text(spec.get("label") or spec.get("type")),
                            _clean_text(spec.get("value")),
                            _clean_text(spec.get("unit")),
                        ]
                        if part
                    )
                )

        for procedure in payload.get("procedures") or []:
            if isinstance(procedure, dict):
                parts.append(_clean_text(procedure.get("instruction") or procedure.get("step")))

        technician_view = payload.get("technician_view") or {}
        quick_reference = technician_view.get("quick_reference") or {}
        for bucket_name in ["torque", "fluids"]:
            for row in quick_reference.get(bucket_name) or []:
                if isinstance(row, dict):
                    parts.append(
                        " ".join(
                            part
                            for part in [
                                _clean_text(row.get("label") or row.get("name")),
                                _clean_text(row.get("value")),
                                _clean_text(row.get("unit")),
                            ]
                            if part
                        )
                    )
        for card in technician_view.get("step_cards") or []:
            if isinstance(card, dict):
                parts.append(_clean_text(card.get("instruction_original") or card.get("instruction")))

    return "\n".join(part for part in parts if part)


def _score(question_tokens: Set[str], query_text: str, item: Dict[str, Any]) -> int:
    if not question_tokens:
        return 0

    haystack = _flatten_record_text(item)
    haystack_tokens = set(_tokenize(haystack))
    overlap = len(question_tokens & haystack_tokens)
    if overlap <= 0:
        return 0

    normalized_query = _normalize_text(query_text)
    title_text = _normalize_text(item.get("title") or item.get("file_name"))
    page_text = _normalize_text(item.get("page_content"))
    score = overlap * 4

    if normalized_query and normalized_query in page_text:
        score += 10
    if normalized_query and normalized_query in title_text:
        score += 14

    for token in question_tokens:
        if token and token in title_text:
            score += 3
        if token and token in page_text:
            score += 1

    return score


def _build_structured_summary(records: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    torque_specs: List[str] = []
    other_specs: List[str] = []
    steps: List[str] = []
    seen: Set[str] = set()

    def add(bucket: List[str], text: Any, limit: int) -> None:
        normalized = _clean_text(text)
        if not normalized or normalized in seen or len(bucket) >= limit:
            return
        seen.add(normalized)
        bucket.append(normalized)

    for item in records or []:
        for payload in _iter_manual_payloads(item):
            technician_view = payload.get("technician_view") or {}
            quick_reference = technician_view.get("quick_reference") or {}

            for spec in payload.get("specs") or []:
                if not isinstance(spec, dict):
                    continue
                label = _clean_text(spec.get("label") or spec.get("type") or "参数")
                value = _clean_text(spec.get("value"))
                unit = _clean_text(spec.get("unit"))
                text = " ".join(part for part in [label, value, unit] if part).strip()
                if str(spec.get("type") or "").lower() == "torque":
                    add(torque_specs, text, 6)
                else:
                    add(other_specs, text, 8)

            for item_spec in (quick_reference.get("torque") or [])[:8]:
                if not isinstance(item_spec, dict):
                    continue
                add(
                    torque_specs,
                    " ".join(
                        part
                        for part in [
                            _clean_text(item_spec.get("label")),
                            _clean_text(item_spec.get("value")),
                            _clean_text(item_spec.get("unit")),
                        ]
                        if part
                    ),
                    6,
                )

            for item_spec in (quick_reference.get("fluids") or [])[:8]:
                if not isinstance(item_spec, dict):
                    continue
                add(
                    other_specs,
                    " ".join(
                        part
                        for part in [
                            _clean_text(item_spec.get("label") or item_spec.get("name")),
                            _clean_text(item_spec.get("value")),
                            _clean_text(item_spec.get("unit")),
                        ]
                        if part
                    ),
                    8,
                )

            specifications = payload.get("specifications") or {}
            for row in specifications.get("spec_table_rows") or []:
                if not isinstance(row, dict):
                    continue
                add(
                    other_specs,
                    " | ".join(
                        part
                        for part in [
                            _clean_text(row.get("item")),
                            _clean_text(row.get("standard_value")),
                            _clean_text(row.get("limit_value")),
                            _clean_text(row.get("tool")),
                            _clean_text(row.get("model")),
                        ]
                        if part
                    ),
                    8,
                )

            for procedure in payload.get("procedures") or []:
                if isinstance(procedure, dict):
                    add(steps, procedure.get("instruction") or procedure.get("step") or "", 6)

            for card in (technician_view.get("step_cards") or [])[:6]:
                if isinstance(card, dict):
                    add(steps, card.get("instruction_original") or card.get("instruction") or "", 6)

    return {
        "torque_specs": torque_specs[:6],
        "other_specs": other_specs[:8],
        "steps": steps[:6],
    }


def query_kb(query_text: str, collection_name: str = "manuals") -> Dict[str, Any]:
    path = _collection_path(collection_name)
    if not path.exists():
        return {"answer": "当前资料库还没有导入对应手册。", "sources": [], "context": "", "structured_summary": {}}

    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"answer": "资料库索引读取失败。", "sources": [], "context": "", "structured_summary": {}}

    question_tokens = set(_tokenize(query_text))
    ranked_with_score = sorted(
        (
            {
                "score": _score(question_tokens, query_text, item),
                "item": item,
            }
            for item in records
        ),
        key=lambda row: row["score"],
        reverse=True,
    )
    ranked = [row["item"] for row in ranked_with_score if row["score"] > 0][:4]
    if not ranked:
        ranked = records[:3]

    context_parts = [str(item.get("page_content", "")).strip()[:1000] for item in ranked]
    context_text = "\n\n---\n\n".join(part for part in context_parts if part)
    sources = [
        {
            "page": item.get("page", "unknown"),
            "title": _clean_text(item.get("title") or item.get("file_name") or "知识文档"),
        }
        for item in ranked
    ]
    structured_summary = _build_structured_summary(ranked)

    answer = "已从知识库命中最相关的维修资料片段，可结合当前车辆或工单上下文继续细化。\n\n"
    answer += context_text[:2200] if context_text else "暂时没有找到可用的知识库内容。"
    return {
        "answer": answer,
        "sources": sources,
        "context": context_text,
        "structured_summary": structured_summary,
    }
