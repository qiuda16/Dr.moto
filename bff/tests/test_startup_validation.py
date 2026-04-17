from app.main import collect_production_startup_issues
from app.core.config import settings


def test_production_startup_validation_wechat_missing_keys():
    original = {
        "SECRET_KEY": settings.SECRET_KEY,
        "ADMIN_PASSWORD": settings.ADMIN_PASSWORD,
        "ADMIN_PASSWORD_HASH": settings.ADMIN_PASSWORD_HASH,
        "ENABLE_DEV_ENDPOINTS": settings.ENABLE_DEV_ENDPOINTS,
        "ENABLE_MOCK_PAYMENT": settings.ENABLE_MOCK_PAYMENT,
        "PAYMENT_PROVIDER": settings.PAYMENT_PROVIDER,
        "WEBHOOK_SHARED_SECRET": settings.WEBHOOK_SHARED_SECRET,
        "PAYMENT_WEBHOOK_SECRET": settings.PAYMENT_WEBHOOK_SECRET,
        "WECHAT_MCH_ID": settings.WECHAT_MCH_ID,
        "WECHAT_APP_ID": settings.WECHAT_APP_ID,
        "WECHAT_API_V3_KEY": settings.WECHAT_API_V3_KEY,
        "WECHAT_CERT_SERIAL_NO": settings.WECHAT_CERT_SERIAL_NO,
        "WECHAT_NOTIFY_URL": settings.WECHAT_NOTIFY_URL,
        "WECHAT_MCH_PRIVATE_KEY_PEM": settings.WECHAT_MCH_PRIVATE_KEY_PEM,
        "WECHAT_MCH_PRIVATE_KEY_PATH": settings.WECHAT_MCH_PRIVATE_KEY_PATH,
    }
    try:
        settings.SECRET_KEY = "strong-secret"
        settings.ADMIN_PASSWORD = "strong-password"
        settings.ADMIN_PASSWORD_HASH = None
        settings.ENABLE_DEV_ENDPOINTS = False
        settings.ENABLE_MOCK_PAYMENT = False
        settings.PAYMENT_PROVIDER = "wechat"
        settings.WEBHOOK_SHARED_SECRET = "hook-secret"
        settings.PAYMENT_WEBHOOK_SECRET = "pay-secret"
        settings.WECHAT_MCH_ID = None
        settings.WECHAT_APP_ID = None
        settings.WECHAT_API_V3_KEY = None
        settings.WECHAT_CERT_SERIAL_NO = None
        settings.WECHAT_NOTIFY_URL = None
        settings.WECHAT_MCH_PRIVATE_KEY_PEM = None
        settings.WECHAT_MCH_PRIVATE_KEY_PATH = None

        issues = collect_production_startup_issues()
        assert any("BFF_WECHAT_MCH_ID" in issue for issue in issues)
        assert any("BFF_WECHAT_MCH_PRIVATE_KEY_PEM or BFF_WECHAT_MCH_PRIVATE_KEY_PATH" in issue for issue in issues)
    finally:
        for key, value in original.items():
            setattr(settings, key, value)

