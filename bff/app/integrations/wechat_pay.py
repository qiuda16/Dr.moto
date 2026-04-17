from dataclasses import dataclass
import base64
import json
from pathlib import Path
import time
import uuid

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from ..core.config import settings


@dataclass
class WeChatPrepayResult:
    code_url: str
    prepay_id: str | None
    raw: dict


class WeChatPayClient:
    def __init__(self):
        self.api_base = settings.WECHAT_API_BASE.rstrip("/")
        self.timeout_seconds = settings.WECHAT_TIMEOUT_SECONDS

    def _validate_config(self):
        missing = []
        for key, value in (
            ("WECHAT_MCH_ID", settings.WECHAT_MCH_ID),
            ("WECHAT_APP_ID", settings.WECHAT_APP_ID),
            ("WECHAT_CERT_SERIAL_NO", settings.WECHAT_CERT_SERIAL_NO),
        ):
            if not value:
                missing.append(key)
        if not settings.WECHAT_MCH_PRIVATE_KEY_PEM and not settings.WECHAT_MCH_PRIVATE_KEY_PATH:
            missing.append("WECHAT_MCH_PRIVATE_KEY_PEM or WECHAT_MCH_PRIVATE_KEY_PATH")
        if missing:
            raise RuntimeError(f"WeChat pay is not fully configured, missing: {', '.join(missing)}")

    def _load_private_key(self):
        pem_text = settings.WECHAT_MCH_PRIVATE_KEY_PEM
        if settings.WECHAT_MCH_PRIVATE_KEY_PATH:
            key_path = Path(settings.WECHAT_MCH_PRIVATE_KEY_PATH)
            if not key_path.exists():
                raise RuntimeError(f"WECHAT_MCH_PRIVATE_KEY_PATH does not exist: {key_path}")
            pem_text = key_path.read_text(encoding="utf-8")

        if not pem_text:
            raise RuntimeError("No merchant private key configured")

        try:
            return serialization.load_pem_private_key(
                pem_text.encode("utf-8"),
                password=None,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load WECHAT_MCH_PRIVATE_KEY_PEM: {exc}") from exc

    def _build_authorization_header(self, method: str, path: str, body: str) -> str:
        self._validate_config()
        private_key = self._load_private_key()

        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex[:16]
        message = f"{method}\n{path}\n{timestamp}\n{nonce_str}\n{body}\n"
        signature = private_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        return (
            f'WECHATPAY2-SHA256-RSA2048 mchid="{settings.WECHAT_MCH_ID}",'
            f'nonce_str="{nonce_str}",timestamp="{timestamp}",'
            f'serial_no="{settings.WECHAT_CERT_SERIAL_NO}",signature="{signature_b64}"'
        )

    def create_native_prepay(
        self,
        out_trade_no: str,
        amount_fen: int,
        description: str,
        store_id: str,
    ) -> WeChatPrepayResult:
        if amount_fen <= 0:
            raise RuntimeError("amount_fen must be positive")

        notify_url = settings.WECHAT_NOTIFY_URL or "https://example.com/mp/payments/webhook/wechat"
        path = "/v3/pay/transactions/native"
        url = f"{self.api_base}{path}"
        payload = {
            "appid": settings.WECHAT_APP_ID,
            "mchid": settings.WECHAT_MCH_ID,
            "description": description[:127],
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "attach": store_id,
            "amount": {
                "total": int(amount_fen),
                "currency": "CNY",
            },
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        authorization = self._build_authorization_header("POST", path, body)
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "drmoto-bff/1.0",
        }

        resp = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=self.timeout_seconds)
        if resp.status_code >= 300:
            raise RuntimeError(f"WeChat prepay request failed: status={resp.status_code}, body={resp.text}")

        data = resp.json()
        code_url = data.get("code_url")
        if not code_url:
            raise RuntimeError(f"WeChat prepay response missing code_url: {data}")
        return WeChatPrepayResult(
            code_url=code_url,
            prepay_id=data.get("prepay_id"),
            raw=data,
        )


wechat_pay_client = WeChatPayClient()


def _load_platform_public_key():
    pem_text = settings.WECHAT_PLATFORM_PUBLIC_KEY_PEM
    if settings.WECHAT_PLATFORM_PUBLIC_KEY_PATH:
        key_path = Path(settings.WECHAT_PLATFORM_PUBLIC_KEY_PATH)
        if not key_path.exists():
            raise RuntimeError(f"WECHAT_PLATFORM_PUBLIC_KEY_PATH does not exist: {key_path}")
        pem_text = key_path.read_text(encoding="utf-8")

    if not pem_text:
        return None

    try:
        return serialization.load_pem_public_key(pem_text.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to load WeChat platform public key: {exc}") from exc


def verify_wechat_callback_signature(
    raw_body: bytes,
    timestamp: str | None,
    nonce: str | None,
    signature_b64: str | None,
    serial: str | None,
) -> bool:
    if not timestamp or not nonce or not signature_b64:
        return False

    if settings.WECHAT_PLATFORM_CERT_SERIAL_NO and serial:
        if settings.WECHAT_PLATFORM_CERT_SERIAL_NO.strip() != serial.strip():
            return False

    public_key = _load_platform_public_key()
    if public_key is None:
        return False

    message = f"{timestamp}\n{nonce}\n{raw_body.decode('utf-8', errors='replace')}\n"
    try:
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
