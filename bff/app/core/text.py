import re
import unicodedata
from pathlib import Path
from typing import Optional
from uuid import uuid4


def normalize_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return unicodedata.normalize("NFC", value).replace("\x00", "").strip()


def build_storage_object_name(prefix: str, original_name: Optional[str]) -> str:
    normalized_name = normalize_text(original_name) or "upload.bin"
    suffix = Path(normalized_name).suffix or ".bin"

    # Keep object paths ASCII-safe for MinIO presigned URLs while preserving
    # the original filename separately in the database.
    return f"{prefix}/{uuid4().hex}{suffix.lower()}"


def compact_whitespace(value: Optional[str]) -> Optional[str]:
    normalized = normalize_text(value)
    if normalized is None:
        return None
    return re.sub(r"\s+", " ", normalized)
