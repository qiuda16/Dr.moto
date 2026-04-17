from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..core.text import compact_whitespace, normalize_text

STORE_NAME_MAX = 120
BRAND_NAME_MAX = 80
BADGE_TEXT_MAX = 40
DELIVERY_NOTE_MAX = 255
HEX_COLOR_MAX = 32
PHRASE_MAX = 120
MAX_PHRASES = 12


class AppSettingsBase(BaseModel):
    store_name: str = Field(default="机车博士", max_length=STORE_NAME_MAX)
    brand_name: str = Field(default="DrMoto", max_length=BRAND_NAME_MAX)
    sidebar_badge_text: Optional[str] = Field(default="门店管理", max_length=BADGE_TEXT_MAX)
    primary_color: str = Field(default="#409EFF", max_length=HEX_COLOR_MAX)
    default_labor_price: Optional[float] = Field(default=80, ge=0)
    default_delivery_note: Optional[str] = Field(default="已向客户说明施工内容，建议按期复检。", max_length=DELIVERY_NOTE_MAX)
    common_complaint_phrases: list[str] = Field(default_factory=list, max_length=MAX_PHRASES)

    @field_validator("store_name", "brand_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("Field is required")
        return normalized

    @field_validator("sidebar_badge_text", "default_delivery_note", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("primary_color")
    @classmethod
    def validate_primary_color(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("primary_color is required")
        if not normalized.startswith("#") or len(normalized) not in {4, 7}:
            raise ValueError("primary_color must be a hex color like #409EFF")
        return normalized.upper()

    @field_validator("common_complaint_phrases", mode="before")
    @classmethod
    def normalize_phrase_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("common_complaint_phrases must be a list")
        normalized_items: list[str] = []
        for item in value:
            normalized = compact_whitespace(str(item or ""))
            if not normalized:
                continue
            if len(normalized) > PHRASE_MAX:
                raise ValueError(f"Phrase too long (>{PHRASE_MAX})")
            normalized_items.append(normalized)
        if len(normalized_items) > MAX_PHRASES:
            raise ValueError(f"Too many phrases (>{MAX_PHRASES})")
        return normalized_items


class AppSettingsUpdate(AppSettingsBase):
    pass


class AppSettingsResponse(AppSettingsBase):
    store_id: str
    updated_by: Optional[str] = None

