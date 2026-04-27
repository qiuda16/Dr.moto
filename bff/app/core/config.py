from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List, Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "DrMoto BFF"
    VERSION: str = "0.1.0"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024
    BFF_MAX_REQUEST_BODY_BYTES: Optional[int] = None
    DEFAULT_STORE_ID: str = "default"
    CORS_ORIGINS: str = "*"
    ENABLE_DEV_ENDPOINTS: bool = True
    ENABLE_MOCK_PAYMENT: bool = True
    PAYMENT_PROVIDER: str = "mock"
    PAYMENT_WEBHOOK_SECRET: Optional[str] = None
    WECHAT_MCH_ID: Optional[str] = None
    WECHAT_APP_ID: Optional[str] = None
    WECHAT_APP_SECRET: Optional[str] = None
    WECHAT_API_V3_KEY: Optional[str] = None
    WECHAT_CERT_SERIAL_NO: Optional[str] = None
    WECHAT_MCH_PRIVATE_KEY_PEM: Optional[str] = None
    WECHAT_MCH_PRIVATE_KEY_PATH: Optional[str] = None
    WECHAT_NOTIFY_URL: Optional[str] = None
    WECHAT_API_BASE: str = "https://api.mch.weixin.qq.com"
    WECHAT_TIMEOUT_SECONDS: int = 10
    WECHAT_PLATFORM_CERT_SERIAL_NO: Optional[str] = None
    WECHAT_PLATFORM_PUBLIC_KEY_PEM: Optional[str] = None
    WECHAT_PLATFORM_PUBLIC_KEY_PATH: Optional[str] = None
    
    # Database
    DATABASE_URL: str = "postgresql://odoo:odoo@db:5432/bff"
    BFF_DATABASE_URL: Optional[str] = None
    MYSQL_ADDRESS: Optional[str] = None
    MYSQL_USERNAME: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_DATABASE: str = "flask_demo"
    MYSQL_PORT: int = 3306
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_POOL_PRE_PING: bool = True
    DB_AUTO_CREATE_TABLES: Optional[bool] = None
    MIGRATIONS_DIR: str = "migrations/versions"
    AUTO_APPLY_MIGRATIONS: bool = False
    
    # Odoo
    ODOO_URL: str = "http://odoo:8069"
    ODOO_DB: str = "odoo"
    ODOO_USER: str = "admin"
    ODOO_PASSWORD: str = "admin"
    ODOO_TIMEOUT_SECONDS: int = 10
    ODOO_RETRY_MAX_ATTEMPTS: int = 3
    ODOO_RETRY_BACKOFF_SECONDS: float = 0.5
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    BFF_REDIS_URL: Optional[str] = None
    
    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123456"
    MINIO_BUCKET: str = "drmoto"

    # AI / OCR
    AI_URL: str = "http://ai:8000"
    AI_PROXY_TIMEOUT_SECONDS: float = 300.0
    AI_PROXY_POOL_TIMEOUT_SECONDS: float = 1.0
    AI_PROXY_MAX_INFLIGHT: int = 24
    AI_PROXY_QUEUE_WAIT_SECONDS: float = 1.2
    AI_PREFETCH_TIMEOUT_SECONDS: float = 6.0
    OCR_REQUEST_TIMEOUT_SECONDS: int = 1800

    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 600

    # Security
    SECRET_KEY: str = "your-secret-key-change-me-in-production"
    BFF_SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@drmoto.local"
    ADMIN_ROLE: str = "admin"
    ADMIN_PASSWORD: str = "change_me_now"
    ADMIN_PASSWORD_HASH: Optional[str] = None
    WEBHOOK_SHARED_SECRET: Optional[str] = None

    # Rate Limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300
    STRICT_STARTUP_VALIDATION: bool = True
    BFF_ENV: Optional[str] = None
    BFF_ENABLE_DEV_ENDPOINTS: Optional[bool] = None
    BFF_WECHAT_APP_ID: Optional[str] = None
    BFF_WECHAT_APP_SECRET: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }

    @field_validator("ENV")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def apply_compat_env(self):
        # 兼容旧变量前缀 BFF_*
        if self.BFF_ENV and (not self.ENV or self.ENV == "dev"):
            self.ENV = self.BFF_ENV
        if self.BFF_ENABLE_DEV_ENDPOINTS is not None:
            self.ENABLE_DEV_ENDPOINTS = self.BFF_ENABLE_DEV_ENDPOINTS
        if self.BFF_WECHAT_APP_ID and not self.WECHAT_APP_ID:
            self.WECHAT_APP_ID = self.BFF_WECHAT_APP_ID
        if self.BFF_WECHAT_APP_SECRET and not self.WECHAT_APP_SECRET:
            self.WECHAT_APP_SECRET = self.BFF_WECHAT_APP_SECRET
        if self.BFF_SECRET_KEY and self.SECRET_KEY == "your-secret-key-change-me-in-production":
            self.SECRET_KEY = self.BFF_SECRET_KEY
        if self.BFF_REDIS_URL and self.REDIS_URL == "redis://redis:6379/0":
            self.REDIS_URL = self.BFF_REDIS_URL
        if self.BFF_DATABASE_URL and self.DATABASE_URL == "postgresql://odoo:odoo@db:5432/bff":
            self.DATABASE_URL = self.BFF_DATABASE_URL
        if self.BFF_MAX_REQUEST_BODY_BYTES is not None:
            self.MAX_REQUEST_BODY_BYTES = int(self.BFF_MAX_REQUEST_BODY_BYTES)

        # 兼容 wxcloudrun-flask MySQL 变量：MYSQL_ADDRESS / MYSQL_USERNAME / MYSQL_PASSWORD
        if self.MYSQL_ADDRESS and self.MYSQL_USERNAME and self.MYSQL_PASSWORD:
            if self.DATABASE_URL == "postgresql://odoo:odoo@db:5432/bff":
                addr = self.MYSQL_ADDRESS.strip()
                if ":" in addr:
                    host, port = addr.rsplit(":", 1)
                    try:
                        port_int = int(port)
                    except ValueError:
                        host = addr
                        port_int = int(self.MYSQL_PORT)
                else:
                    host = addr
                    port_int = int(self.MYSQL_PORT)
                db_name = (self.MYSQL_DATABASE or "flask_demo").strip() or "flask_demo"
                self.DATABASE_URL = (
                    f"mysql+pymysql://{self.MYSQL_USERNAME}:{self.MYSQL_PASSWORD}"
                    f"@{host}:{port_int}/{db_name}?charset=utf8mb4"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENV in {"prod", "production"}

    @property
    def cors_origins(self) -> List[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def auto_create_tables(self) -> bool:
        if self.DB_AUTO_CREATE_TABLES is not None:
            return self.DB_AUTO_CREATE_TABLES
        return not self.is_production

settings = Settings()
