import time
import json
from typing import Optional, Dict, Any
import httpx
from api.src.services.payment.base import (
    PaymentProvider,
    OrderResult,
    CaptureResult,
    PayoutResult,
    RefundResult,
    WebhookVerificationResult,
)


class PayPalError(Exception):
    """Exception raised for PayPal API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class PayPalSandboxPaymentProvider(PaymentProvider):
    """
    Live PayPal Sandbox Payment Provider.
    Implements OAuth2 token caching, idempotent Orders v2, Payouts, Captures refund,
    and webhook signature verification.
    """

    BASE_URL = "https://api-m.sandbox.paypal.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_id: Optional[str] = None,
    ):
        if not client_id or not client_secret:
            raise ValueError("PayPal client_id and client_secret are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_id = webhook_id
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _get_access_token(self) -> str:
        """Fetch or refresh OAuth2 client_credentials token with 60s buffer."""
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 60):
            return self._access_token

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
            )
            if resp.status_code != 200:
                raise PayPalError(
                    f"PayPal OAuth token failed: {resp.status_code} - {resp.text}",
                    status_code=resp.status_code,
                )
            data = resp.json()
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 32400)
            self._token_expires_at = now + expires_in
            return self._access_token

    async def _auth_headers(self, request_id: Optional[str] = None) -> Dict[str, str]:
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        return headers

    async def create_order(
        self,
        donation_id: str,
        amount: float,
        currency: str = "USD",
        request_id: Optional[str] = None,
    ) -> OrderResult:
        if amount <= 0:
            raise ValueError("Donation amount must be positive")

        headers = await self._auth_headers(request_id=request_id or f"ord_{donation_id}")
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": donation_id,
                    "custom_id": donation_id,
                    "description": f"Donation {donation_id} held by Vouch",
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": f"{amount:.2f}",
                    },
                }
            ],
            "application_context": {
                "brand_name": "Vouch Platform",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": "https://vouch.app/checkout/success",
                "cancel_url": "https://vouch.app/checkout/cancel",
            },
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/checkout/orders",
                json=payload,
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                raise PayPalError(f"Create order failed: {resp.text}", resp.status_code)
            data = resp.json()

            approve_url = None
            for link in data.get("links", []):
                if link.get("rel") == "approve":
                    approve_url = link.get("href")
                    break

            return OrderResult(
                order_id=data["id"],
                status=data["status"],
                amount=amount,
                currency=currency.upper(),
                custom_id=donation_id,
                approve_url=approve_url,
                raw_response=data,
            )

    async def capture_order(
        self,
        order_id: str,
        request_id: Optional[str] = None,
    ) -> CaptureResult:
        headers = await self._auth_headers(request_id=request_id or f"cap_{order_id}")
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                raise PayPalError(f"Capture order failed: {resp.text}", resp.status_code)
            data = resp.json()

            capture_id = ""
            amount = 0.0
            currency = "USD"
            try:
                pu = data["purchase_units"][0]
                cap = pu["payments"]["captures"][0]
                capture_id = cap["id"]
                amount = float(cap["amount"]["value"])
                currency = cap["amount"]["currency_code"]
                status = cap["status"]
            except (KeyError, IndexError, ValueError):
                status = data.get("status", "COMPLETED")

            return CaptureResult(
                capture_id=capture_id,
                order_id=order_id,
                status=status,
                amount=amount,
                currency=currency,
                raw_response=data,
            )

    async def get_order(self, order_id: str) -> OrderResult:
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/v2/checkout/orders/{order_id}",
                headers=headers,
            )
            if resp.status_code != 200:
                raise PayPalError(f"Get order failed: {resp.text}", resp.status_code)
            data = resp.json()
            amount = float(data["purchase_units"][0]["amount"]["value"])
            currency = data["purchase_units"][0]["amount"]["currency_code"]
            custom_id = data["purchase_units"][0].get("custom_id")
            return OrderResult(
                order_id=data["id"],
                status=data["status"],
                amount=amount,
                currency=currency,
                custom_id=custom_id,
                raw_response=data,
            )

    async def get_capture(self, capture_id: str) -> CaptureResult:
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/v2/payments/captures/{capture_id}",
                headers=headers,
            )
            if resp.status_code != 200:
                raise PayPalError(f"Get capture failed: {resp.text}", resp.status_code)
            data = resp.json()
            return CaptureResult(
                capture_id=data["id"],
                order_id=data.get("custom_id", ""),
                status=data["status"],
                amount=float(data["amount"]["value"]),
                currency=data["amount"]["currency_code"],
                raw_response=data,
            )

    async def create_payout(
        self,
        release_id: str,
        receiver_email: str,
        amount: float,
        currency: str = "USD",
        note: str = "Vouch verified release payment",
    ) -> PayoutResult:
        if amount <= 0:
            raise ValueError("Payout amount must be positive")

        headers = await self._auth_headers()
        payload = {
            "sender_batch_header": {
                "sender_batch_id": release_id,
                "email_subject": "You have received a verified donation release through Vouch",
                "email_message": note,
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": currency.upper(),
                    },
                    "note": note,
                    "sender_item_id": f"item_{release_id}",
                    "receiver": receiver_email,
                }
            ],
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/payments/payouts",
                json=payload,
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                raise PayPalError(f"Create payout failed: {resp.text}", resp.status_code)
            data = resp.json()
            batch_id = data["batch_header"]["payout_batch_id"]
            batch_status = data["batch_header"]["batch_status"]

            return PayoutResult(
                payout_batch_id=batch_id,
                status=batch_status,
                receiver_email=receiver_email,
                amount=amount,
                currency=currency.upper(),
                sender_batch_id=release_id,
                raw_response=data,
            )

    async def get_payout(self, payout_batch_id: str) -> PayoutResult:
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/v1/payments/payouts/{payout_batch_id}",
                headers=headers,
            )
            if resp.status_code != 200:
                raise PayPalError(f"Get payout failed: {resp.text}", resp.status_code)
            data = resp.json()
            header = data["batch_header"]
            items = data.get("items", [])
            receiver = items[0]["payout_item"]["receiver"] if items else ""
            amount = float(items[0]["payout_item"]["amount"]["value"]) if items else 0.0
            currency = items[0]["payout_item"]["amount"]["currency"] if items else "USD"

            return PayoutResult(
                payout_batch_id=header["payout_batch_id"],
                status=header["batch_status"],
                receiver_email=receiver,
                amount=amount,
                currency=currency,
                sender_batch_id=header.get("sender_batch_header", {}).get("sender_batch_id", ""),
                raw_response=data,
            )

    async def refund_capture(
        self,
        capture_id: str,
        amount: float,
        request_id: str,
        currency: str = "USD",
        note: str = "Vouch unproven deadline refund",
    ) -> RefundResult:
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        headers = await self._auth_headers(request_id=request_id)
        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency_code": currency.upper(),
            },
            "note_to_payer": note,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/payments/captures/{capture_id}/refund",
                json=payload,
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                raise PayPalError(f"Refund capture failed: {resp.text}", resp.status_code)
            data = resp.json()

            return RefundResult(
                refund_id=data["id"],
                capture_id=capture_id,
                status=data["status"],
                amount=float(data["amount"]["value"]),
                currency=data["amount"]["currency_code"],
                raw_response=data,
            )

    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        if not self.webhook_id:
            raise PayPalError("PAYPAL_WEBHOOK_ID not configured")

        # PayPal webhook signature verification expects these exact header keys:
        transmission_id = headers.get("paypal-transmission-id") or headers.get("PAYPAL-TRANSMISSION-ID")
        transmission_time = headers.get("paypal-transmission-time") or headers.get("PAYPAL-TRANSMISSION-TIME")
        transmission_sig = headers.get("paypal-transmission-sig") or headers.get("PAYPAL-TRANSMISSION-SIG")
        cert_url = headers.get("paypal-cert-url") or headers.get("PAYPAL-CERT-URL")
        auth_algo = headers.get("paypal-auth-algo") or headers.get("PAYPAL-AUTH-ALGO")

        if not all([transmission_id, transmission_time, transmission_sig, cert_url, auth_algo]):
            return WebhookVerificationResult(
                verified=False,
                status="MISSING_SIGNATURE_HEADERS",
                resource={},
            )

        try:
            body_json = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return WebhookVerificationResult(
                verified=False,
                status="INVALID_JSON_BODY",
                resource={},
            )

        verify_payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": self.webhook_id,
            "webhook_event": body_json,
        }

        auth_hdrs = await self._auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/notifications/verify-webhook-signature",
                json=verify_payload,
                headers=auth_hdrs,
            )
            if resp.status_code != 200:
                return WebhookVerificationResult(
                    verified=False,
                    status=f"VERIFY_CALL_FAILED_{resp.status_code}",
                    resource={},
                )
            result = resp.json()
            is_valid = result.get("verification_status") == "SUCCESS"
            return WebhookVerificationResult(
                verified=is_valid,
                status=result.get("verification_status", "UNKNOWN"),
                event_type=body_json.get("event_type"),
                event_id=body_json.get("id"),
                resource=body_json.get("resource", {}),
            )
