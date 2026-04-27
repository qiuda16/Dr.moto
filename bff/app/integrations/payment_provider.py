from __future__ import annotations

from dataclasses import dataclass
import hmac
import hashlib

from ..core.config import settings
from .wechat_pay import wechat_pay_client, verify_wechat_callback_signature


@dataclass
class PaymentIntentResult:
    payment_url: str
    status: str


SUPPORTED_PROVIDERS = {"mock", "wechat"}


def build_payment_intent(
    provider: str,
    transaction_id: str,
    amount: float,
    amount_fen: int,
    work_order_id: str,
    store_id: str,
    base_url: str,
) -> PaymentIntentResult:
    normalized = (provider or settings.PAYMENT_PROVIDER or "mock").strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported payment provider: {provider}")

    if normalized == "mock":
        if not settings.ENABLE_MOCK_PAYMENT:
            raise RuntimeError("Mock payment provider is disabled")
        return PaymentIntentResult(
            payment_url=f"{base_url}/mp/payments/mock_gateway?id={transaction_id}&amount={amount}&store_id={store_id}",
            status="pending",
        )

    prepay = wechat_pay_client.create_native_prepay(
        out_trade_no=transaction_id,
        amount_fen=amount_fen,
        description=f"DrMoto WorkOrder {work_order_id}",
        store_id=store_id,
    )
    return PaymentIntentResult(
        payment_url=prepay.code_url,
        status="pending",
    )


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    if not settings.PAYMENT_WEBHOOK_SECRET:
        return True
    if not signature:
        return False
    digest = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature.strip().lower())


def verify_provider_webhook_signature(
    provider: str,
    raw_body: bytes,
    signature: str | None,
    headers: dict[str, str],
) -> bool:
    normalized = (provider or "").strip().lower()

    if normalized == "wechat":
        wx_ok = verify_wechat_callback_signature(
            raw_body=raw_body,
            timestamp=headers.get("wechatpay-timestamp"),
            nonce=headers.get("wechatpay-nonce"),
            signature_b64=headers.get("wechatpay-signature"),
            serial=headers.get("wechatpay-serial"),
        )
        if wx_ok:
            return True
        # Backward-compatible fallback for environments still using shared-secret callback verification.
        return verify_webhook_signature(raw_body, signature)

    return verify_webhook_signature(raw_body, signature)
