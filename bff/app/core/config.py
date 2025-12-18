from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "DrMoto BFF"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = "postgresql://odoo:odoo@db:5432/bff"
    
    # Odoo
    ODOO_URL: str = "http://odoo:8069"
    ODOO_DB: str = "odoo"
    ODOO_USER: str = "odoo"
    ODOO_PASSWORD: str = "odoo"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123456"
    MINIO_BUCKET: str = "drmoto"
    
    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 600

    # Security
    SECRET_KEY: str = "your-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
