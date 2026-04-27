import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


logger = logging.getLogger("ai.memory")

AI_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = AI_ROOT / "data"
MEMORY_ROOT = DATA_ROOT / "memory"
SESSION_MEMORY_PATH = MEMORY_ROOT / "session_memory.json"
MEMORY_BACKEND = os.getenv("AI_MEMORY_BACKEND", "redis").strip().lower()
MEMORY_REDIS_URL = os.getenv("AI_MEMORY_REDIS_URL", "redis://redis:6379/1").strip()
MEMORY_KEEP_RECENT_TURNS = int(os.getenv("AI_MEMORY_KEEP_RECENT_TURNS", "12"))
MEMORY_MAX_TURNS = int(os.getenv("AI_MEMORY_MAX_TURNS", "20"))
MEMORY_WARM_NOTES_MAX = int(os.getenv("AI_MEMORY_WARM_NOTES_MAX", "80"))
MEMORY_WORKING_BUFFER_MAX = int(os.getenv("AI_MEMORY_WORKING_BUFFER_MAX", "60"))
MEMORY_COLD_FACTS_MAX = int(os.getenv("AI_MEMORY_COLD_FACTS_MAX", "32"))


def _extract_generic_fact_tags(question: str, answer: str) -> list[str]:
    text = f"{question or ''}\n{answer or ''}"
    tags: list[str] = []

    for match in re.findall(r"\b([A-Z]{2,}-\d{4,})\b", text.upper()):
        value = _compact_text(match)
        if value:
            tags.append(f"fact_code:{value}")

    for match in re.findall(r"第\s*([0-9]{1,3})\s*轮", text):
        value = _compact_text(match)
        if value:
            tags.append(f"fact_round:{value}")

    normalized_question = str(question or "").lower()
    if any(token in normalized_question for token in ["记住", "记一下", "记着", "记下来", "remember"]):
        compact_question = _compact_text(question)[:160]
        if compact_question:
            tags.append(f"fact_note:{compact_question}")

    return list(dict.fromkeys(tags))


def _ensure_memory_root() -> None:
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)


def _compact_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())


def _memory_key(user_id: str) -> str:
    return f"drmoto:ai:memory:{user_id}"


def _redis_client():
    if MEMORY_BACKEND != "redis" or redis is None:
        return None
    try:
        return redis.Redis.from_url(MEMORY_REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("Failed to init redis memory client: %s", exc)
        return None


def _load_file_store() -> dict[str, Any]:
    _ensure_memory_root()
    if not SESSION_MEMORY_PATH.exists():
        return {}
    try:
        return json.loads(SESSION_MEMORY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load session memory file: %s", exc)
        return {}


def _save_file_store(payload: dict[str, Any]) -> None:
    _ensure_memory_root()
    SESSION_MEMORY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _normalize_user_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {
            "summary": "",
            "turns": payload,
            "warm_notes": [],
            "cold_facts": {},
            "working_buffer": [],
        }
    if isinstance(payload, dict):
        return {
            "summary": _compact_text(payload.get("summary")),
            "turns": list(payload.get("turns") or []),
            "warm_notes": list(payload.get("warm_notes") or []),
            "cold_facts": dict(payload.get("cold_facts") or {}),
            "working_buffer": list(payload.get("working_buffer") or []),
        }
    return {"summary": "", "turns": [], "warm_notes": [], "cold_facts": {}, "working_buffer": []}


def _safe_json_compact(value: Any, max_chars: int = 1000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = _compact_text(str(value))
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _upsert_cold_fact(cold_facts: dict[str, Any], key: str, value: str) -> None:
    normalized_key = _compact_text(key)
    normalized_value = _compact_text(value)
    if not normalized_key or not normalized_value:
        return
    cold_facts[normalized_key] = {
        "value": normalized_value[:240],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _update_cold_facts(cold_facts: dict[str, Any], memory_item: dict[str, Any]) -> dict[str, Any]:
    result = dict(cold_facts or {})
    tags = [_compact_text(tag) for tag in (memory_item.get("tags") or []) if _compact_text(tag)]
    for tag in tags:
        lower = tag.lower()
        if lower.startswith("customer_id:"):
            _upsert_cold_fact(result, "customer_id", tag.split(":", 1)[-1])
        elif lower.startswith("fact_code:"):
            _upsert_cold_fact(result, "fact_code", tag.split(":", 1)[-1])
        elif lower.startswith("fact_round:"):
            _upsert_cold_fact(result, "fact_round", tag.split(":", 1)[-1])
        elif lower.startswith("fact_note:"):
            _upsert_cold_fact(result, "fact_note", tag.split(":", 1)[-1])
        elif re.fullmatch(r"[A-Z0-9-]{5,16}", tag.upper()) and any(ch.isdigit() for ch in tag):
            _upsert_cold_fact(result, "plate", tag)
        elif len(tag) >= 32 and tag.count("-") >= 4:
            _upsert_cold_fact(result, "work_order_id", tag)

    question = _compact_text(memory_item.get("question"))
    answer = _compact_text(memory_item.get("answer"))
    for source in [question, answer]:
        if not source:
            continue
        work_order_match = re.search(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", source.lower())
        if work_order_match:
            _upsert_cold_fact(result, "work_order_id", work_order_match.group(0))
        code_match = re.search(r"\b([A-Z]{2,}-\d{4,})\b", source.upper())
        if code_match:
            _upsert_cold_fact(result, "fact_code", code_match.group(1))

    if len(result) > MEMORY_COLD_FACTS_MAX:
        ordered = sorted(
            result.items(),
            key=lambda item: _compact_text((item[1] or {}).get("updated_at")),
            reverse=True,
        )
        result = dict(ordered[:MEMORY_COLD_FACTS_MAX])
    return result


def _load_user_memory(user_id: str) -> dict[str, Any]:
    if not user_id:
        return {"summary": "", "turns": []}

    client = _redis_client()
    if client is not None:
        try:
            raw = client.get(_memory_key(user_id))
            if not raw:
                return {"summary": "", "turns": []}
            return _normalize_user_payload(json.loads(raw))
        except Exception as exc:
            logger.warning("Failed to load redis session memory: %s", exc)

    store = _load_file_store()
    return _normalize_user_payload(store.get(user_id))


def _save_user_memory(user_id: str, payload: dict[str, Any]) -> None:
    normalized = _normalize_user_payload(payload)
    client = _redis_client()
    if client is not None:
        try:
            client.set(_memory_key(user_id), json.dumps(normalized, ensure_ascii=False))
            return
        except Exception as exc:
            logger.warning("Failed to save redis session memory: %s", exc)

    store = _load_file_store()
    store[user_id] = normalized
    _save_file_store(store)


def _summarize_turns(turns: list[dict[str, Any]]) -> str:
    if not turns:
        return ""
    lines: list[str] = []
    for item in turns[-8:]:
        question = _compact_text(item.get("question"))[:80]
        answer = _compact_text(item.get("answer"))[:120]
        tags = [str(tag).strip() for tag in (item.get("tags") or []) if str(tag).strip()]
        line = f"- 问：{question}；答：{answer}"
        if tags:
            line += f"；标签：{' / '.join(tags[:4])}"
        lines.append(line)
    return "\n".join(lines)


def _merge_summary(old_summary: str, archived_turns: list[dict[str, Any]]) -> str:
    archived_summary = _summarize_turns(archived_turns)
    if old_summary and archived_summary:
        return (old_summary + "\n" + archived_summary).strip()[:4000]
    return (old_summary or archived_summary).strip()[:4000]


def recall_session_memory(user_id: str, query: str = "", limit: int = 4) -> list[dict[str, Any]]:
    if not user_id:
        return []
    payload = _load_user_memory(user_id)
    items = list(payload.get("turns") or [])
    if not items:
        return []

    normalized_query = _compact_text(query).lower()
    if normalized_query:
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            haystack = " ".join(
                [
                    _compact_text(item.get("question")),
                    _compact_text(item.get("answer")),
                    " ".join(_compact_text(tag) for tag in item.get("tags") or []),
                ]
            ).lower()
            score = 0
            for token in normalized_query.split():
                if token and token in haystack:
                    score += 1
            if score > 0:
                scored.append((score, item))
        if scored:
            scored.sort(key=lambda pair: pair[0], reverse=True)
            return [item for _, item in scored[:limit]]

    return items[-limit:]


def recall_session_summary(user_id: str) -> str:
    if not user_id:
        return ""
    payload = _load_user_memory(user_id)
    return _compact_text(payload.get("summary"))[:4000]


def recall_memory_anchor(user_id: str) -> dict[str, str]:
    if not user_id:
        return {}
    payload = _load_user_memory(user_id)
    turns = list(payload.get("turns") or [])
    if not turns:
        return {}

    anchor: dict[str, str] = {}
    ignored_tag_prefixes = ("fact_", "knowledge_", "project_", "source_", "type:")
    ignored_exact_tags = {
        "kb",
        "knowledge",
        "business_context",
        "catalog",
        "store_ops",
        "work_order",
        "customer",
        "vehicle",
    }
    for item in reversed(turns):
        for tag in item.get("tags") or []:
            value = _compact_text(tag)
            if not value:
                continue
            lower = value.lower()
            if lower in ignored_exact_tags or lower.startswith(ignored_tag_prefixes):
                continue
            if not anchor.get("customer_id") and lower.startswith("customer_id:"):
                parsed = value.split(":", 1)[-1].strip()
                if parsed.isdigit():
                    anchor["customer_id"] = parsed
            elif not anchor.get("work_order_id") and len(lower) >= 32 and lower.count("-") >= 4:
                anchor["work_order_id"] = value
            elif not anchor.get("plate"):
                upper_value = value.upper()
                is_cn_plate = bool(
                    re.fullmatch(
                        r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6}",
                        upper_value,
                    )
                )
                is_generic_plate = bool(
                    re.fullmatch(r"[A-Z0-9-]{5,16}", upper_value) and any(ch.isdigit() for ch in upper_value)
                )
                if is_cn_plate or is_generic_plate:
                    anchor["plate"] = value
            elif not anchor.get("customer_name"):
                anchor["customer_name"] = value
        if anchor.get("work_order_id") or anchor.get("plate") or anchor.get("customer_id"):
            break
    return anchor


def recall_generic_memory_facts(user_id: str) -> dict[str, str]:
    if not user_id:
        return {}
    payload = _load_user_memory(user_id)
    turns = list(payload.get("turns") or [])
    if not turns:
        return {}

    facts: dict[str, str] = {}
    for item in reversed(turns):
        for tag in item.get("tags") or []:
            value = _compact_text(tag)
            lower = value.lower()
            if not facts.get("fact_code") and lower.startswith("fact_code:"):
                facts["fact_code"] = value.split(":", 1)[-1].strip()
            elif not facts.get("fact_round") and lower.startswith("fact_round:"):
                facts["fact_round"] = value.split(":", 1)[-1].strip()
            elif not facts.get("fact_note") and lower.startswith("fact_note:"):
                facts["fact_note"] = value.split(":", 1)[-1].strip()
        if facts.get("fact_code") and facts.get("fact_round"):
            break
    return facts


def remember_session_turn(
    user_id: str,
    question: str,
    answer: str,
    business_context: Optional[dict[str, Any]] = None,
    sources: Optional[list[dict[str, Any]]] = None,
) -> None:
    if not user_id:
        return

    matched_customer = ((business_context or {}).get("matched_customer") or {}).get("name")
    matched_customer_id = ((business_context or {}).get("matched_customer") or {}).get("id")
    matched_vehicle = ((business_context or {}).get("matched_vehicle") or {}).get("license_plate") or (
        (business_context or {}).get("matched_vehicle") or {}
    ).get("vehicle_plate")
    matched_work_order = ((business_context or {}).get("matched_work_order") or {}).get("id")
    if not matched_customer:
        customer_match = re.search(
            r"(?:客户|车主)\s*[:：]?\s*([A-Za-z\u4e00-\u9fa5]{2,12})(?:的|[，,\s。]|$)",
            str(question or ""),
        )
        if customer_match:
            matched_customer = customer_match.group(1)
    if not matched_work_order:
        answer_match = re.search(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", str(answer or "").lower())
        if answer_match:
            matched_work_order = answer_match.group(0)
    if not matched_vehicle:
        plate_match = re.search(
            r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6}",
            str(answer or "").upper(),
        )
        if plate_match:
            matched_vehicle = plate_match.group(0)
    if not matched_vehicle:
        plate_match = re.search(
            r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6}",
            str(question or "").upper(),
        )
        if plate_match:
            matched_vehicle = plate_match.group(0)
    source_types = [str(item.get("type") or "").strip() for item in (sources or []) if item]

    memory_item = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "question": _compact_text(question)[:400],
        "answer": _compact_text(answer)[:1200],
        "tags": [
            tag
            for tag in [
                _compact_text(matched_customer),
                _compact_text(f"customer_id:{matched_customer_id}" if matched_customer_id is not None else ""),
                _compact_text(matched_vehicle),
                _compact_text(matched_work_order),
                *[_compact_text(tag) for tag in _extract_generic_fact_tags(question, answer)],
                *[_compact_text(tag) for tag in source_types[:6]],
            ]
            if tag
        ],
    }

    payload = _load_user_memory(user_id)
    history = list(payload.get("turns") or [])
    warm_notes = [_compact_text(item) for item in (payload.get("warm_notes") or []) if _compact_text(item)]
    cold_facts = dict(payload.get("cold_facts") or {})
    history.append(memory_item)
    history = history[-MEMORY_MAX_TURNS:]

    if len(history) > MEMORY_KEEP_RECENT_TURNS:
        archived = history[:-MEMORY_KEEP_RECENT_TURNS]
        history = history[-MEMORY_KEEP_RECENT_TURNS:]
        payload["summary"] = _merge_summary(payload.get("summary", ""), archived)
        for item in archived:
            question = _compact_text(item.get("question"))[:80]
            answer = _compact_text(item.get("answer"))[:120]
            if question or answer:
                warm_notes.append(f"{question} => {answer}".strip(" =>"))

    payload["turns"] = history
    payload["warm_notes"] = warm_notes[-MEMORY_WARM_NOTES_MAX:]
    payload["cold_facts"] = _update_cold_facts(cold_facts, memory_item)
    _save_user_memory(user_id, payload)


def remember_working_event(
    user_id: str,
    event: str,
    *,
    status: str = "ok",
    payload: Optional[dict[str, Any]] = None,
) -> None:
    if not user_id or not _compact_text(event):
        return
    memory_payload = _load_user_memory(user_id)
    buffer = list(memory_payload.get("working_buffer") or [])
    buffer.append(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "event": _compact_text(event)[:80],
            "status": _compact_text(status, "ok")[:40],
            "payload": _safe_json_compact(payload or {}, max_chars=1000),
        }
    )
    memory_payload["working_buffer"] = buffer[-MEMORY_WORKING_BUFFER_MAX:]
    _save_user_memory(user_id, memory_payload)


def recall_memory_tiers(
    user_id: str,
    *,
    hot_limit: int = 4,
    warm_limit: int = 6,
    cold_limit: int = 12,
    buffer_limit: int = 6,
) -> dict[str, Any]:
    if not user_id:
        return {"hot": [], "warm": [], "cold": [], "working_buffer": []}
    payload = _load_user_memory(user_id)
    hot_items = list(payload.get("turns") or [])[-max(1, hot_limit) :]
    warm_items = [_compact_text(item) for item in (payload.get("warm_notes") or []) if _compact_text(item)]
    working_buffer = list(payload.get("working_buffer") or [])[-max(1, buffer_limit) :]
    cold_raw = dict(payload.get("cold_facts") or {})
    ordered_cold = sorted(
        cold_raw.items(),
        key=lambda item: _compact_text((item[1] or {}).get("updated_at")),
        reverse=True,
    )
    cold_items = []
    for key, item in ordered_cold[: max(1, cold_limit)]:
        if not isinstance(item, dict):
            continue
        value = _compact_text(item.get("value"))
        if not value:
            continue
        cold_items.append({"key": _compact_text(key), "value": value, "updated_at": _compact_text(item.get("updated_at"))})
    return {
        "hot": hot_items,
        "warm": warm_items[-max(1, warm_limit) :],
        "cold": cold_items,
        "working_buffer": working_buffer,
    }
