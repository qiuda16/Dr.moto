from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class CustomerWechatLoginRequest(BaseModel):
    code: str
    store_id: str = "default"

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "wx-login-code-123",
                "store_id": "default",
            }
        }
    }


class CustomerWechatLoginResponse(BaseModel):
    bound: bool
    bind_ticket: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    partner_id: Optional[int] = None
    customer_name: Optional[str] = None
    phone_masked: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "bound": False,
                "bind_ticket": "f47ac10b58cc4372a5670e02b2c3d479",
                "access_token": None,
                "refresh_token": None,
                "expires_in": None,
                "partner_id": None,
                "customer_name": None,
                "phone_masked": None,
            }
        }
    }


class CustomerBindRequest(BaseModel):
    bind_ticket: str
    phone: str
    plate_no: str
    verify_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "bind_ticket": "f47ac10b58cc4372a5670e02b2c3d479",
                "phone": "13800138000",
                "plate_no": "沪A12345",
                "verify_code": "123456",
            }
        }
    }


class CustomerBindResponse(BaseModel):
    bound: bool
    access_token: str
    refresh_token: str
    expires_in: int
    partner_id: int
    customer_name: str
    phone_masked: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "bound": True,
                "access_token": "eyJhbGciOi...",
                "refresh_token": "a3db2f3f57d9456ea0d8fb640f...",
                "expires_in": 1800,
                "partner_id": 101,
                "customer_name": "Alice Rider",
                "phone_masked": "138****8000",
            }
        }
    }


class CustomerRefreshRequest(BaseModel):
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "a3db2f3f57d9456ea0d8fb640f...",
            }
        }
    }


class CustomerRefreshResponse(BaseModel):
    access_token: str
    expires_in: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOi...",
                "expires_in": 1800,
            }
        }
    }


class CustomerProfileResponse(BaseModel):
    partner_id: int
    customer_name: str
    phone_masked: Optional[str] = None
    store_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "partner_id": 101,
                "customer_name": "Alice Rider",
                "phone_masked": "138****8000",
                "store_id": "default",
            }
        }
    }


class CustomerVehicleResponse(BaseModel):
    id: int
    license_plate: str
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    engine_code: Optional[str] = None
    catalog_model_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 201,
                "license_plate": "沪A12345",
                "vin": "VINTEST001",
                "make": "Yamaha",
                "model": "NMAX",
                "year": 2023,
                "engine_code": "E-155",
                "catalog_model_id": 12,
            }
        }
    }


class CustomerHomeSummaryResponse(BaseModel):
    latest_odometer_km: Optional[float] = None
    health_records_count: int = 0
    pending_recommendations: int = 0
    latest_order_status: Optional[str] = None
    latest_measured_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "latest_odometer_km": 15873.2,
                "health_records_count": 6,
                "pending_recommendations": 3,
                "latest_order_status": "done",
                "latest_measured_at": "2026-03-30T10:00:00+08:00",
            }
        }
    }


class CustomerMaintenanceListResponse(BaseModel):
    page: int
    size: int
    total: int
    items: list[dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "size": 20,
                "total": 2,
                "items": [
                    {
                        "id": 401,
                        "name": "WO-401",
                        "vehicle_plate": "沪A12345",
                        "state": "done",
                        "date_planned": "2026-03-30 10:00:00",
                        "amount_total": 199.0,
                    }
                ],
            }
        }
    }


class CustomerSubscriptionPrefUpsert(BaseModel):
    vehicle_id: Optional[int] = None
    notify_enabled: bool = True
    remind_before_days: int = 7
    remind_before_km: int = 500
    prefer_channel: str = "wechat_subscribe"

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": 201,
                "notify_enabled": True,
                "remind_before_days": 7,
                "remind_before_km": 500,
                "prefer_channel": "wechat_subscribe",
            }
        }
    }
