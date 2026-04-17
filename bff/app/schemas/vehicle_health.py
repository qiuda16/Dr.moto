from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, field_validator

from ..core.text import compact_whitespace, normalize_text


class VehicleHealthRecordCreate(BaseModel):
    measured_at: Optional[datetime] = None
    odometer_km: float
    engine_rpm: Optional[float] = None
    battery_voltage: Optional[float] = None
    tire_front_psi: Optional[float] = None
    tire_rear_psi: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    oil_life_percent: Optional[float] = None
    notes: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    @field_validator("odometer_km")
    @classmethod
    def validate_odometer(cls, value: float) -> float:
        if value < 0:
            raise ValueError("odometer_km must be >= 0")
        return float(value)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return normalize_text(value)


class VehicleHealthRecordResponse(BaseModel):
    id: int
    customer_id: str
    vehicle_plate: str
    measured_at: datetime
    odometer_km: float
    engine_rpm: Optional[float] = None
    battery_voltage: Optional[float] = None
    tire_front_psi: Optional[float] = None
    tire_rear_psi: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    oil_life_percent: Optional[float] = None
    notes: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    odometer_delta_from_prev: Optional[float] = None
    days_since_prev: Optional[float] = None
