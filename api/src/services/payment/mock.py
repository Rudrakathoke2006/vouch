import uuid
from typing import Optional, Dict, Any
from api.src.services.payment.base import (
    PaymentProvider,
    OrderResult,
    CaptureResult,
    PayoutResult,
    RefundResult,
    WebhookVerificationResult,
)


class MockPaymentError(Exception):
    """Exception raised for simulated payment failures."""
    pass


class MockPaymentProvider(PaymentProvider):
    """
    Deterministic in-memory Mock Payment Provider.
    Enforces idempotency, verifies state transitions, and supports simulated failure modes
    (timeouts, duplicates, denied payouts, network errors) to prove money invariants.
    """

    def __init__(
        self,
        simulate_timeout: bool = False,
        simulate_payout_denied: bool = False,
        simulate_network_error: bool = False,
    ):
        self.simulate_timeout = simulate_timeout
        self.simulate_payout_denied = simulate_payout_denied
        self.simulate_network_error = simulate_network_error

        # In-memory stores
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.captures: Dict[str, Dict[str, Any]] = {}
        self.payouts: Dict[str, Dict[str, Any]] = {}
        self.refunds: Dict[str, Dict[str, Any]] = {}

        # Idempotency caches
        self.idempotency_keys: Dict[str, Any] = {}

    def reset(self):
        """Reset all in-memory mock states."""
        self.orders.clear()
        self.captures.clear()
        self.payouts.clear()
        self.refunds.clear()
        self.idempotency_keys.clear()

    async def create_order(
        self,
        donation_id: str,
        amount: float,
        currency: str = "USD",
        request_id: Optional[str] = None,
    ) -> OrderResult:
        if self.simulate_timeout:
            raise MockPaymentError("MockTimeoutError: PayPal API gateway timeout")
        if self.simulate_network_error:
            raise MockPaymentError("MockNetworkError: Connection reset by peer")
        if amount <= 0:
            raise ValueError(f"Order amount must be positive, got {amount}")

        # Check idempotency
        idemp_key = request_id or f"order_{donation_id}"
        if idemp_key in self.idempotency_keys:
            cached = self.idempotency_keys[idemp_key]
            return OrderResult(**cached)

        order_id = f"mock_order_{uuid.uuid4().hex[:12]}"
        order_data = {
            "order_id": order_id,
            "status": "CREATED",
            "amount": float(amount),
            "currency": currency.upper(),
            "custom_id": donation_id,
            "approve_url": f"https://sandbox.vouch.mock/checkout?token={order_id}",
            "raw_response": {"id": order_id, "status": "CREATED", "intent": "CAPTURE"},
        }

        self.orders[order_id] = order_data
        self.idempotency_keys[idemp_key] = order_data
        return OrderResult(**order_data)

    async def capture_order(
        self,
        order_id: str,
        request_id: Optional[str] = None,
    ) -> CaptureResult:
        if self.simulate_timeout:
            raise MockPaymentError("MockTimeoutError: PayPal API gateway timeout")

        idemp_key = request_id or f"capture_{order_id}"
        if idemp_key in self.idempotency_keys:
            cached = self.idempotency_keys[idemp_key]
            return CaptureResult(**cached)

        if order_id not in self.orders:
            raise MockPaymentError(f"MockOrderNotFound: Order {order_id} does not exist")

        order = self.orders[order_id]
        if order["status"] == "COMPLETED":
            # Order was already captured
            for cap in self.captures.values():
                if cap["order_id"] == order_id:
                    return CaptureResult(**cap)

        capture_id = f"mock_cap_{uuid.uuid4().hex[:12]}"
        capture_data = {
            "capture_id": capture_id,
            "order_id": order_id,
            "status": "COMPLETED",
            "amount": order["amount"],
            "currency": order["currency"],
            "raw_response": {"id": capture_id, "status": "COMPLETED"},
        }

        order["status"] = "COMPLETED"
        self.captures[capture_id] = capture_data
        self.idempotency_keys[idemp_key] = capture_data
        return CaptureResult(**capture_data)

    async def get_order(self, order_id: str) -> OrderResult:
        if order_id not in self.orders:
            raise MockPaymentError(f"MockOrderNotFound: Order {order_id} not found")
        return OrderResult(**self.orders[order_id])

    async def get_capture(self, capture_id: str) -> CaptureResult:
        if capture_id not in self.captures:
            raise MockPaymentError(f"MockCaptureNotFound: Capture {capture_id} not found")
        return CaptureResult(**self.captures[capture_id])

    async def create_payout(
        self,
        release_id: str,
        receiver_email: str,
        amount: float,
        currency: str = "USD",
        note: str = "Vouch verified release payment",
    ) -> PayoutResult:
        if self.simulate_timeout:
            raise MockPaymentError("MockTimeoutError: PayPal Payouts timeout")
        if amount <= 0:
            raise ValueError(f"Payout amount must be positive, got {amount}")

        # Enforce idempotency on sender_batch_id = release_id
        if release_id in self.idempotency_keys:
            cached = self.idempotency_keys[release_id]
            return PayoutResult(**cached)

        if self.simulate_payout_denied:
            raise MockPaymentError("MockPayoutDenied: Payout rejected by compliance check")

        batch_id = f"mock_batch_{uuid.uuid4().hex[:12]}"
        payout_data = {
            "payout_batch_id": batch_id,
            "status": "SUCCESS",
            "receiver_email": receiver_email,
            "amount": float(amount),
            "currency": currency.upper(),
            "sender_batch_id": release_id,
            "raw_response": {
                "batch_header": {
                    "payout_batch_id": batch_id,
                    "batch_status": "SUCCESS",
                    "sender_batch_header": {"sender_batch_id": release_id},
                }
            },
        }

        self.payouts[batch_id] = payout_data
        self.idempotency_keys[release_id] = payout_data
        return PayoutResult(**payout_data)

    async def get_payout(self, payout_batch_id: str) -> PayoutResult:
        if payout_batch_id not in self.payouts:
            raise MockPaymentError(f"MockPayoutNotFound: Payout {payout_batch_id} not found")
        return PayoutResult(**self.payouts[payout_batch_id])

    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        request_id: str,
        currency: str = "USD",
        note: str = "Vouch unproven deadline refund",
    ) -> RefundResult:
        if self.simulate_timeout:
            raise MockPaymentError("MockTimeoutError: PayPal Refund timeout")
        if amount <= 0:
            raise ValueError(f"Refund amount must be positive, got {amount}")

        # Idempotency check on request_id
        if request_id in self.idempotency_keys:
            cached = self.idempotency_keys[request_id]
            return RefundResult(**cached)

        if capture_id not in self.captures:
            raise MockPaymentError(f"MockCaptureNotFound: Capture {capture_id} does not exist")

        capture = self.captures[capture_id]
        if amount > capture["amount"]:
            raise ValueError(f"Refund amount {amount} exceeds capture amount {capture['amount']}")

        # Enforce single refund invariant per capture in mock
        for ref in self.refunds.values():
            if ref["capture_id"] == capture_id:
                raise MockPaymentError(f"MockDuplicateRefundError: Capture {capture_id} already refunded")

        refund_id = f"mock_ref_{uuid.uuid4().hex[:12]}"
        refund_data = {
            "refund_id": refund_id,
            "capture_id": capture_id,
            "status": "COMPLETED",
            "amount": float(amount),
            "currency": currency.upper(),
            "raw_response": {"id": refund_id, "status": "COMPLETED"},
        }

        self.refunds[refund_id] = refund_data
        self.idempotency_keys[request_id] = refund_data
        return RefundResult(**refund_data)

    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        """In mock mode, accept mock signatures and parse JSON payload."""
        import json
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            body = {}

        sig = headers.get("PAYPAL-TRANSMISSION-SIG", "")
        # Reject if signature header is explicitly "INVALID"
        if sig == "INVALID":
            return WebhookVerificationResult(
                verified=False,
                status="FAILURE",
                resource={},
            )

        return WebhookVerificationResult(
            verified=True,
            status="SUCCESS",
            event_type=body.get("event_type", "CHECKOUT.ORDER.APPROVED"),
            event_id=body.get("id", f"mock_evt_{uuid.uuid4().hex[:8]}"),
            resource=body.get("resource", {}),
        )
