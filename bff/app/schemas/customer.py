from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from ..core.text import compact_whitespace, normalize_text


CUSTOMER_NAME_MAX = 80
CUSTOMER_PHONE_MAX = 40
CUSTOMER_EMAIL_MAX = 120
LICENSE_PLATE_MAX = 30
VEHICLE_BRAND_MAX = 80
VEHICLE_MODEL_MAX = 120
ENGINE_CODE_MAX = 80
VIN_MAX = 64
COLOR_MAX = 40


class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=CUSTOMER_NAME_MAX)
    phone: Optional[str] = Field(default=None, max_length=CUSTOMER_PHONE_MAX)
    email: Optional[str] = Field(default=None, max_length=CUSTOMER_EMAIL_MAX)
    vehicles: List["CustomerVehicleCreate"] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("Customer name is required")
        return normalized

    @field_validator("phone", "email", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value):
        return normalize_text(value)


class CustomerVehicleCreate(BaseModel):
    catalog_model_id: Optional[int] = None
    license_plate: str = Field(..., max_length=LICENSE_PLATE_MAX)
    make: str = Field(..., max_length=VEHICLE_BRAND_MAX)
    model: str = Field(..., max_length=VEHICLE_MODEL_MAX)
    year: int
    engine_code: Optional[str] = Field(default=None, max_length=ENGINE_CODE_MAX)
    vin: Optional[str] = Field(default=None, max_length=VIN_MAX)
    color: Optional[str] = Field(default=None, max_length=COLOR_MAX)

    @field_validator("license_plate", "make", "model")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("Field is required")
        return normalized

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if value < 1950 or value > 2100:
            raise ValueError("Invalid vehicle year")
        return value

    @field_validator("engine_code", "vin", "color", mode="before")
    @classmethod
    def normalize_optional_vehicle_fields(cls, value):
        return normalize_text(value)


class CustomerVehicleResponse(BaseModel):
    id: int
    partner_id: int
    catalog_model_id: Optional[int] = None
    license_plate: str
    vin: Optional[str] = None
    color: Optional[str] = None
    vehicle_id: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    engine_code: Optional[str] = None


class CustomerWithVehiclesResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    vehicle_count: int = 0
    vehicles: List[CustomerVehicleResponse] = []


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=CUSTOMER_NAME_MAX)
    phone: Optional[str] = Field(default=None, max_length=CUSTOMER_PHONE_MAX)
    email: Optional[str] = Field(default=None, max_length=CUSTOMER_EMAIL_MAX)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("Customer name cannot be empty")
        return normalized

    @field_validator("phone", "email", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value):
        return normalize_text(value)


class CustomerVehicleUpdate(BaseModel):
    catalog_model_id: Optional[int] = None
    license_plate: Optional[str] = Field(default=None, max_length=LICENSE_PLATE_MAX)
    make: Optional[str] = Field(default=None, max_length=VEHICLE_BRAND_MAX)
    model: Optional[str] = Field(default=None, max_length=VEHICLE_MODEL_MAX)
    year: Optional[int] = None
    engine_code: Optional[str] = Field(default=None, max_length=ENGINE_CODE_MAX)
    vin: Optional[str] = Field(default=None, max_length=VIN_MAX)
    color: Optional[str] = Field(default=None, max_length=COLOR_MAX)

    @field_validator("license_plate", "make", "model", mode="before")
    @classmethod
    def normalize_required_like_fields(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("Field cannot be empty string")
        return normalized

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 1950 or value > 2100:
            raise ValueError("Invalid vehicle year")
        return value

    @field_validator("engine_code", "vin", "color", mode="before")
    @classmethod
    def normalize_optional_vehicle_fields(cls, value):
        return normalize_text(value)


CustomerCreate.model_rebuild()
