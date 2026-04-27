from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import requests


logger = logging.getLogger("ai.openclaw")


OPENCLAW_CONFIG_JSON = os.getenv("OPENCLAW_CONFIG_JSON", "/app/data/provider/openclaw.json").strip()
OPENCLAW_MODELS_JSON = os.getenv("OPENCLAW_MODELS_JSON", "/app/data/provider/models.json").strip()
OPENCLAW_TIMEOUT_SECONDS = int(os.getenv("OPENCLAW_TIMEOUT_SECONDS", "300"))
OPENCLAW_PROVIDER_KEY = os.getenv("OPENCLAW_PROVIDER_KEY", "").strip()
OPENCLAW_PROVIDER_MODEL = os.getenv("OPENCLAW_PROVIDER_MODEL", "").strip()
OPENCLAW_PROVIDER_BASE_URL = os.getenv("OPENCLAW_PROVIDER_BASE_URL", "").strip().rstrip("/")
OPENCLAW_PROVIDER_API = os.getenv("OPENCLAW_PROVIDER_API", "").strip()
OPENCLAW_PROVIDER_API_KEY = os.getenv("OPENCLAW_PROVIDER_API_KEY", "").strip()
OPENCLAW_PROVIDER_AUTH_HEADER = os.getenv("OPENCLAW_PROVIDER_AUTH_HEADER", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _safe_read_json(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def load_openclaw_model_config() -> dict[str, Any]:
    config = _safe_read_json(OPENCLAW_CONFIG_JSON)
    models = _safe_read_json(OPENCLAW_MODELS_JSON)
    return {"config": config, "models": models}


def _normalize_provider_key(primary_ref: str) -> tuple[str, str]:
    text = str(primary_ref or "").strip()
    if "/" in text:
        provider_key, model_id = text.split("/", 1)
        return provider_key.strip(), model_id.strip()
    return "", text


def resolve_openclaw_primary_target() -> dict[str, Any]:
    if OPENCLAW_PROVIDER_MODEL and OPENCLAW_PROVIDER_BASE_URL and OPENCLAW_PROVIDER_API:
        provider_key = OPENCLAW_PROVIDER_KEY or "openclaw-custom"
        return {
            "provider_key": provider_key,
            "model_id": OPENCLAW_PROVIDER_MODEL,
            "base_url": OPENCLAW_PROVIDER_BASE_URL,
            "api": OPENCLAW_PROVIDER_API,
            "api_key": OPENCLAW_PROVIDER_API_KEY,
            "auth_header": OPENCLAW_PROVIDER_AUTH_HEADER,
        }

    payload = load_openclaw_model_config()
    config = payload.get("config") or {}
    models = payload.get("models") or {}
    primary_ref = (
        ((config.get("agents") or {}).get("defaults") or {}).get("model") or {}
    ).get("primary")
    provider_key, model_id = _normalize_provider_key(str(primary_ref or ""))
    providers = (models.get("providers") or {}) if isinstance(models, dict) else {}

    provider = {}
    if provider_key:
        provider = dict(providers.get(provider_key) or {})
    if not provider and providers:
        provider_key = next(iter(providers.keys()))
        provider = dict(providers.get(provider_key) or {})

    model_items = list(provider.get("models") or [])
    if not model_id and model_items:
        model_id = str((model_items[0] or {}).get("id") or "").strip()
    if model_id and model_items:
        chosen = next((item for item in model_items if str((item or {}).get("id") or "") == model_id), None)
        if chosen:
            model_id = str(chosen.get("id") or "").strip()

    return {
        "provider_key": provider_key,
        "model_id": model_id,
        "base_url": str(provider.get("baseUrl") or "").rstrip("/"),
        "api": str(provider.get("api") or "").strip(),
        "api_key": str(provider.get("apiKey") or "").strip(),
        "auth_header": bool(provider.get("authHeader")),
    }


def call_openclaw_text_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    target = resolve_openclaw_primary_target()
    base_url = str(target.get("base_url") or "").rstrip("/")
    model_id = str(target.get("model_id") or "").strip()
    api_name = str(target.get("api") or "").strip().lower()
    api_key = str(target.get("api_key") or "").strip()
    auth_header = bool(target.get("auth_header"))
    provider_key = str(target.get("provider_key") or "").strip() or "openclaw"

    if not (base_url and model_id):
        raise RuntimeError("OpenClaw model config missing base_url or model_id")

    system_lines: list[str] = []
    converted: list[dict[str, Any]] = []
    for message in messages or []:
        role = str((message or {}).get("role") or "").strip().lower()
        content = str((message or {}).get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_lines.append(content)
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        converted.append({"role": role, "content": [{"type": "text", "text": content}]})
    if not converted:
        merged_system = "\n\n".join(system_lines).strip()
        if merged_system:
            converted = [{"role": "user", "content": [{"type": "text", "text": merged_system}]}]
            system_lines = []
        else:
            raise RuntimeError("OpenClaw chat messages are empty")

    headers = {"Content-Type": "application/json"}
    if api_key:
        if auth_header:
            headers["x-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    if api_name == "anthropic-messages":
        headers.setdefault("anthropic-version", "2023-06-01")
        body: dict[str, Any] = {
            "model": model_id,
            "messages": converted,
            "temperature": temperature,
            "max_tokens": max(256, int(max_tokens)),
        }
        merged_system = "\n\n".join(system_lines).strip()
        if merged_system:
            body["system"] = merged_system
        response = requests.post(
            f"{base_url}/messages",
            headers=headers,
            json=body,
            timeout=OPENCLAW_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json() or {}
        chunks = payload.get("content") or []
        parts = []
        for chunk in chunks:
            if isinstance(chunk, dict) and str(chunk.get("type") or "").lower() == "text":
                text = str(chunk.get("text") or "").strip()
                if text:
                    parts.append(text)
        content = "\n".join(parts).strip()
        if content:
            return content
        raise RuntimeError(f"OpenClaw provider {provider_key} returned empty content")

    raise RuntimeError(f"Unsupported OpenClaw provider API: {api_name}")


def call_openclaw_json(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1200,
) -> Optional[dict[str, Any]]:
    content = call_openclaw_text_chat(
        [
            {"role": "system", "content": str(system_prompt or "").strip()},
            {"role": "user", "content": str(user_prompt or "").strip()},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        payload = json.loads(content)
    except Exception as exc:
        candidate = str(content or "").strip()
        if "```" in candidate:
            candidate = candidate.strip("`")
            candidate = candidate.replace("json\n", "", 1).strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(candidate[start : end + 1])
            except Exception:
                logger.warning("OpenClaw JSON parse failed: %s", exc)
                return None
        else:
            logger.warning("OpenClaw JSON parse failed: %s", exc)
            return None
    return payload if isinstance(payload, dict) else None
