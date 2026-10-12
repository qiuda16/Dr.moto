from typing import Optional

from fastapi import Request

from ..schemas.auth import User
from .config import settings
from .text import compact_whitespace


def resolve_store_id(request: Optional[Request], current_user: Optional[User] = None) -> str:
    candidate = None
    if request is not None:
        candidate = request.headers.get("X-Store-Id")
        if not candidate:
            candidate = request.query_params.get("store_id")

    normalized = compact_whitespace(candidate) if candidate else ""
    if normalized:
        return normalized.lower()
    return settings.DEFAULT_STORE_ID
