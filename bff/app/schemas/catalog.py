from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..core.text import compact_whitespace, normalize_text

CATALOG_BRAND_MAX = 80
CATALOG_MODEL_MAX = 120
CATALOG_CATEGORY_MAX = 80
CATALOG_FUEL_MAX = 40
ENGINE_CODE_MAX = 80
SOURCE_MAX = 80
PART_NO_MAX = 80
PART_NAME_MAX = 120
NOTES_MAX = 1000
SERVICE_NAME_MAX = 120
SERVICE_CODE_MAX = 60
PACKAGE_NAME_MAX = 120
PACKAGE_CODE_MAX = 60
UNIT_MAX = 20
SUPPLIER_MAX = 120


class VehicleCatalogModelBase(BaseModel):
    brand: str = Field(..., max_length=CATALOG_BRAND_MAX)
    model_name: str = Field(..., max_length=CATALOG_MODEL_MAX)
    year_from: int
    year_to: Optional[int] = None
    displacement_cc: Optional[int] = None
    category: Optional[str] = Field(default=None, max_length=CATALOG_CATEGORY_MAX)
    fuel_type: Optional[str] = Field(default="gasoline", max_length=CATALOG_FUEL_MAX)
    default_engine_code: Optional[str] = Field(default=None, max_length=ENGINE_CODE_MAX)
    source: Optional[str] = Field(default=None, max_length=SOURCE_MAX)
    is_active: bool = True

    @field_validator("brand", "model_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("brand/model_name is required")
        return normalized

    @field_validator("category", "fuel_type", "default_engine_code", "source", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("year_from", "year_to")
    @classmethod
    def validate_year_range(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 1950 or value > 2100:
            raise ValueError("Invalid year")
        return value


class VehicleCatalogModelCreate(VehicleCatalogModelBase):
    pass


class VehicleCatalogModelUpdate(BaseModel):
    brand: Optional[str] = Field(default=None, max_length=CATALOG_BRAND_MAX)
    model_name: Optional[str] = Field(default=None, max_length=CATALOG_MODEL_MAX)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    displacement_cc: Optional[int] = None
    category: Optional[str] = Field(default=None, max_length=CATALOG_CATEGORY_MAX)
    fuel_type: Optional[str] = Field(default=None, max_length=CATALOG_FUEL_MAX)
    default_engine_code: Optional[str] = Field(default=None, max_length=ENGINE_CODE_MAX)
    source: Optional[str] = Field(default=None, max_length=SOURCE_MAX)
    is_active: Optional[bool] = None

    @field_validator("brand", "model_name", mode="before")
    @classmethod
    def normalize_required_like_text(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("Field cannot be empty")
        return normalized

    @field_validator("category", "fuel_type", "default_engine_code", "source", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("year_from", "year_to")
    @classmethod
    def validate_year_range(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 1950 or value > 2100:
            raise ValueError("Invalid year")
        return value


class VehicleCatalogModelResponse(VehicleCatalogModelBase):
    id: int


class VehicleServiceTemplatePartBase(BaseModel):
    part_id: Optional[int] = None
    part_no: Optional[str] = Field(default=None, max_length=PART_NO_MAX)
    part_name: str = Field(..., max_length=PART_NAME_MAX)
    qty: float = Field(default=1, gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    sort_order: int = 100
    is_optional: bool = False

    @field_validator("part_name")
    @classmethod
    def validate_part_name(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("part_name is required")
        return normalized

    @field_validator("part_no", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)


class VehicleServiceTemplatePartCreate(VehicleServiceTemplatePartBase):
    pass


class VehicleServiceTemplatePartResponse(VehicleServiceTemplatePartBase):
    id: int
    template_item_id: int


class VehicleServiceTemplateItemBase(BaseModel):
    service_name: str = Field(..., max_length=SERVICE_NAME_MAX)
    service_code: Optional[str] = Field(default=None, max_length=SERVICE_CODE_MAX)
    repair_method: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    labor_hours: Optional[float] = None
    labor_price: Optional[float] = Field(default=None, ge=0)
    suggested_price: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    sort_order: int = 100
    is_active: bool = True
    required_parts: list[VehicleServiceTemplatePartCreate] = Field(default_factory=list)

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("service_name is required")
        return normalized

    @field_validator("service_code", "repair_method", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("labor_hours")
    @classmethod
    def validate_labor_hours(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("labor_hours must be >= 0")
        return value


class VehicleServiceTemplateItemCreate(VehicleServiceTemplateItemBase):
    pass


class VehicleServiceTemplateItemUpdate(BaseModel):
    service_name: Optional[str] = Field(default=None, max_length=SERVICE_NAME_MAX)
    service_code: Optional[str] = Field(default=None, max_length=SERVICE_CODE_MAX)
    repair_method: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    labor_hours: Optional[float] = None
    labor_price: Optional[float] = Field(default=None, ge=0)
    suggested_price: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    required_parts: Optional[list[VehicleServiceTemplatePartCreate]] = None

    @field_validator("service_name", mode="before")
    @classmethod
    def normalize_required_like_text(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("service_name cannot be empty")
        return normalized

    @field_validator("service_code", "repair_method", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("labor_hours")
    @classmethod
    def validate_labor_hours(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("labor_hours must be >= 0")
        return value


class VehicleServiceTemplateItemResponse(VehicleServiceTemplateItemBase):
    id: int
    model_id: int


class VehicleServicePackageItemBase(BaseModel):
    template_item_id: int
    sort_order: int = 100
    is_optional: bool = False
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)


class VehicleServicePackageItemCreate(VehicleServicePackageItemBase):
    pass


class VehicleServicePackageItemResponse(VehicleServicePackageItemBase):
    id: int
    package_id: int
    service_item: Optional[VehicleServiceTemplateItemResponse] = None


class VehicleServicePackageBase(BaseModel):
    package_name: str = Field(..., max_length=PACKAGE_NAME_MAX)
    package_code: Optional[str] = Field(default=None, max_length=PACKAGE_CODE_MAX)
    description: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    recommended_interval_km: Optional[int] = None
    recommended_interval_months: Optional[int] = None
    labor_hours_total: Optional[float] = None
    labor_price_total: Optional[float] = Field(default=None, ge=0)
    parts_price_total: Optional[float] = Field(default=None, ge=0)
    suggested_price_total: Optional[float] = Field(default=None, ge=0)
    sort_order: int = 100
    is_active: bool = True
    items: list[VehicleServicePackageItemCreate] = Field(default_factory=list)

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("package_name is required")
        return normalized

    @field_validator("package_code", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)


class VehicleServicePackageCreate(VehicleServicePackageBase):
    pass


class VehicleServicePackageUpdate(BaseModel):
    package_name: Optional[str] = Field(default=None, max_length=PACKAGE_NAME_MAX)
    package_code: Optional[str] = Field(default=None, max_length=PACKAGE_CODE_MAX)
    description: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    recommended_interval_km: Optional[int] = None
    recommended_interval_months: Optional[int] = None
    labor_hours_total: Optional[float] = None
    labor_price_total: Optional[float] = Field(default=None, ge=0)
    parts_price_total: Optional[float] = Field(default=None, ge=0)
    suggested_price_total: Optional[float] = Field(default=None, ge=0)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    items: Optional[list[VehicleServicePackageItemCreate]] = None

    @field_validator("package_name", mode="before")
    @classmethod
    def normalize_required_like_text(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("package_name cannot be empty")
        return normalized

    @field_validator("package_code", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)


class VehicleServicePackageResponse(VehicleServicePackageBase):
    id: int
    model_id: int
    items: list[VehicleServicePackageItemResponse] = Field(default_factory=list)


class PartCatalogItemBase(BaseModel):
    part_no: str = Field(..., max_length=PART_NO_MAX)
    name: str = Field(..., max_length=PART_NAME_MAX)
    brand: Optional[str] = Field(default=None, max_length=CATALOG_BRAND_MAX)
    category: Optional[str] = Field(default=None, max_length=CATALOG_CATEGORY_MAX)
    unit: str = Field(default="件", max_length=UNIT_MAX)
    compatible_model_ids: list[int] = Field(default_factory=list)
    min_stock: Optional[float] = None
    sale_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_qty: Optional[float] = Field(default=None, ge=0)
    supplier_name: Optional[str] = Field(default=None, max_length=SUPPLIER_MAX)
    is_active: bool = True

    @field_validator("part_no", "name", "unit")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = compact_whitespace(value)
        if not normalized:
            raise ValueError("part_no/name/unit is required")
        return normalized

    @field_validator("brand", "category", "supplier_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("min_stock", "sale_price", "cost_price", "stock_qty")
    @classmethod
    def validate_non_negative(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("numeric value must be >= 0")
        return value


class PartCatalogItemCreate(PartCatalogItemBase):
    pass


class PartCatalogItemUpdate(BaseModel):
    part_no: Optional[str] = Field(default=None, max_length=PART_NO_MAX)
    name: Optional[str] = Field(default=None, max_length=PART_NAME_MAX)
    brand: Optional[str] = Field(default=None, max_length=CATALOG_BRAND_MAX)
    category: Optional[str] = Field(default=None, max_length=CATALOG_CATEGORY_MAX)
    unit: Optional[str] = Field(default=None, max_length=UNIT_MAX)
    compatible_model_ids: Optional[list[int]] = None
    min_stock: Optional[float] = None
    sale_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_qty: Optional[float] = Field(default=None, ge=0)
    supplier_name: Optional[str] = Field(default=None, max_length=SUPPLIER_MAX)
    is_active: Optional[bool] = None

    @field_validator("part_no", "name", "unit", mode="before")
    @classmethod
    def normalize_required_like_text(cls, value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        normalized = compact_whitespace(normalized)
        if not normalized:
            raise ValueError("Field cannot be empty")
        return normalized

    @field_validator("brand", "category", "supplier_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return normalize_text(value)

    @field_validator("min_stock", "sale_price", "cost_price", "stock_qty")
    @classmethod
    def validate_non_negative(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("numeric value must be >= 0")
        return value


class PartCatalogItemResponse(PartCatalogItemBase):
    id: int


class BatchDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
