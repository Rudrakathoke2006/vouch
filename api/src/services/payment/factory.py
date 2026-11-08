from api.src.config import settings, PaymentProviderType
from api.src.services.payment.base import PaymentProvider
from api.src.services.payment.mock import MockPaymentProvider
from api.src.services.payment.paypal import PayPalSandboxPaymentProvider


_provider_instance: PaymentProvider | None = None


def get_payment_provider() -> PaymentProvider:
    """Singleton factory for the active payment provider."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if settings.PAYMENT_PROVIDER == PaymentProviderType.PAYPAL_SANDBOX:
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
            raise ValueError(
                "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required when PAYMENT_PROVIDER=paypal_sandbox. "
                "Set them in .env or switch to PAYMENT_PROVIDER=mock."
            )
        _provider_instance = PayPalSandboxPaymentProvider(
            client_id=settings.PAYPAL_CLIENT_ID,
            client_secret=settings.PAYPAL_CLIENT_SECRET,
            webhook_id=settings.PAYPAL_WEBHOOK_ID,
        )
    else:
        _provider_instance = MockPaymentProvider()

    return _provider_instance


def reset_payment_provider():
    """Reset cached provider instance (useful for testing or switching modes)."""
    global _provider_instance
    _provider_instance = None
