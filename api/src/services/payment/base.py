from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel


class OrderResult(BaseModel):
    order_id: str
    status: str
    amount: float
    currency: str
    custom_id: Optional[str] = None
    approve_url: Optional[str] = None
    raw_response: Dict[str, Any] = {}


class CaptureResult(BaseModel):
    capture_id: str
    order_id: str
    status: str
    amount: float
    currency: str
    raw_response: Dict[str, Any] = {}


class PayoutResult(BaseModel):
    payout_batch_id: str
    status: str
    receiver_email: str
    amount: float
    currency: str
    sender_batch_id: str
    raw_response: Dict[str, Any] = {}


class RefundResult(BaseModel):
    refund_id: str
    capture_id: str
    status: str
    amount: float
    currency: str
    raw_response: Dict[str, Any] = {}


class WebhookVerificationResult(BaseModel):
    verified: bool
    status: str
    event_type: Optional[str] = None
    event_id: Optional[str] = None
    resource: Dict[str, Any] = {}


class PaymentProvider(ABC):
    """Abstract interface for payment rails (PayPal Sandbox and deterministic Mock)."""

    @abstractmethod
    async def create_order(
        self,
        donation_id: str,
        amount: float,
        currency: str = "USD",
        request_id: Optional[str] = None,
    ) -> OrderResult:
        """Create a PayPal checkout order with intent=CAPTURE and custom_id=donation_id."""
        pass

    @abstractmethod
    async def capture_order(
        self,
        order_id: str,
        request_id: Optional[str] = None,
    ) -> CaptureResult:
        """Capture funds from an approved order into the platform account."""
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> OrderResult:
        """Fetch order status directly from payment provider."""
        pass

    @abstractmethod
    async def get_capture(self, capture_id: str) -> CaptureResult:
        """Fetch capture status directly from payment provider."""
        pass

    @abstractmethod
    async def create_payout(
        self,
        release_id: str,
        receiver_email: str,
        amount: float,
        currency: str = "USD",
        note: str = "Vouch verified release payment",
    ) -> PayoutResult:
        """Execute a payout to a verified payee using sender_batch_id=release_id."""
        pass

    @abstractmethod
    async def get_payout(self, payout_batch_id: str) -> PayoutResult:
        """Fetch payout batch status directly from payment provider."""
        pass

    @abstractmethod
    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        request_id: str,
        currency: str = "USD",
        note: str = "Vouch unproven deadline refund",
    ) -> RefundResult:
        """Refund a capture pro-rata with PayPal-Request-Id idempotency."""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        """Verify the cryptographic signature of incoming PayPal webhook notifications."""
        pass
