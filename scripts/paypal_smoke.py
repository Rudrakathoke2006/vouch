#!/usr/bin/env python3
"""
PayPal Smoke Test Script for Vouch.
Runs the complete Order -> Capture -> Payout -> Refund lifecycle.
Works seamlessly in both Mock Mode and Live Sandbox Mode.
Prints every generated transaction ID.
"""

import asyncio
import os
import sys
import uuid

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.src.config import settings, PaymentProviderType
from api.src.services.payment.factory import get_payment_provider, reset_payment_provider
from api.src.services.payment.mock import MockPaymentProvider
from api.src.services.payment.paypal import PayPalSandboxPaymentProvider


async def run_smoke_test(force_provider: str = None):
    print("=" * 70)
    print(" VOUCH PAYPAL SMOKE TEST: ORDER -> CAPTURE -> PAYOUT -> REFUND")
    print("=" * 70)

    if force_provider:
        os.environ["PAYMENT_PROVIDER"] = force_provider
        reset_payment_provider()

    provider = get_payment_provider()
    provider_name = "MOCK PROVIDER" if isinstance(provider, MockPaymentProvider) else "PAYPAL SANDBOX"
    print(f"[*] Active Payment Rail: {provider_name}")
    print(f"[*] Timestamp: {asyncio.get_event_loop().time()}")
    print("-" * 70)

    # Synthetic test data
    donation_id = str(uuid.uuid4())
    release_id = str(uuid.uuid4())
    test_amount = 25.00
    payout_amount = 20.00
    refund_amount = 5.00
    payee_email = settings.PAYPAL_RECEIVER_EMAIL or "stjude-sandbox-payee@sandbox.paypal.com"

    try:
        # STEP 1: CREATE ORDER
        print("\n[STEP 1/4] Creating Donation Order...")
        order_req_id = f"smoke_req_ord_{donation_id[:8]}"
        order = await provider.create_order(
            donation_id=donation_id,
            amount=test_amount,
            currency="USD",
            request_id=order_req_id,
        )
        print(f"  [+] Order ID:       {order.order_id}")
        print(f"  [+] Status:         {order.status}")
        print(f"  [+] Amount:         ${order.amount:.2f} {order.currency}")
        print(f"  [+] Custom ID:      {order.custom_id}")
        if order.approve_url:
            print(f"  [+] Approval URL:   {order.approve_url}")

        # Idempotency Verification on Order
        order_retry = await provider.create_order(
            donation_id=donation_id,
            amount=test_amount,
            currency="USD",
            request_id=order_req_id,
        )
        assert order_retry.order_id == order.order_id, "Idempotency check failed for order creation!"
        print("  [OK] Idempotency Verified on Order Creation.")

        # STEP 2: CAPTURE ORDER
        print("\n[STEP 2/4] Capturing Order into Vouch Platform Account...")
        capture_req_id = f"smoke_req_cap_{donation_id[:8]}"
        capture = await provider.capture_order(
            order_id=order.order_id,
            request_id=capture_req_id,
        )
        print(f"  [+] Capture ID:     {capture.capture_id}")
        print(f"  [+] Order ID:       {capture.order_id}")
        print(f"  [+] Status:         {capture.status}")
        print(f"  [+] Captured Amt:   ${capture.amount:.2f} {capture.currency}")

        # Idempotency Verification on Capture
        capture_retry = await provider.capture_order(
            order_id=order.order_id,
            request_id=capture_req_id,
        )
        assert capture_retry.capture_id == capture.capture_id, "Idempotency check failed for capture!"
        print("  [OK] Idempotency Verified on Capture.")

        # STEP 3: CREATE PAYOUT (RELEASE)
        print("\n[STEP 3/4] Releasing Funds to Verified Institutional Payee...")
        payout = await provider.create_payout(
            release_id=release_id,
            receiver_email=payee_email,
            amount=payout_amount,
            currency="USD",
            note="Vouch Smoke Test Payout to Verified Payee",
        )
        print(f"  [+] Payout Batch ID: {payout.payout_batch_id}")
        print(f"  [+] Sender Batch ID: {payout.sender_batch_id}")
        print(f"  [+] Receiver Email:  {payout.receiver_email}")
        print(f"  [+] Status:          {payout.status}")
        print(f"  [+] Payout Amount:   ${payout.amount:.2f} {payout.currency}")

        # Idempotency Verification on Payout
        payout_retry = await provider.create_payout(
            release_id=release_id,
            receiver_email=payee_email,
            amount=payout_amount,
            currency="USD",
        )
        assert payout_retry.payout_batch_id == payout.payout_batch_id, "Idempotency check failed for payout!"
        print("  [OK] Idempotency Verified on Payout Batch.")

        # STEP 4: REFUND UNRELEASED PORTION
        print("\n[STEP 4/4] Refunding Unreleased Funds back to Donor...")
        refund_req_id = f"smoke_req_ref_{donation_id[:8]}"
        refund = await provider.refund_capture(
            capture_id=capture.capture_id,
            amount=refund_amount,
            request_id=refund_req_id,
            currency="USD",
            note="Vouch Smoke Test unspent balance refund",
        )
        print(f"  [+] Refund ID:       {refund.refund_id}")
        print(f"  [+] Capture ID:      {refund.capture_id}")
        print(f"  [+] Status:          {refund.status}")
        print(f"  [+] Refund Amount:   ${refund.amount:.2f} {refund.currency}")

        # Idempotency Verification on Refund
        refund_retry = await provider.refund_capture(
            capture_id=capture.capture_id,
            amount=refund_amount,
            request_id=refund_req_id,
            currency="USD",
        )
        assert refund_retry.refund_id == refund.refund_id, "Idempotency check failed for refund!"
        print("  [OK] Idempotency Verified on Refund.")

        # SUMMARY OF CAPTURED IDENTIFIERS
        print("\n" + "=" * 70)
        print(" ALL TRANSACTION IDS CAPTURED SUCCESSFULLY:")
        print(f"  - DONATION_ID:       {donation_id}")
        print(f"  - PAYPAL_ORDER_ID:   {order.order_id}")
        print(f"  - PAYPAL_CAPTURE_ID: {capture.capture_id}")
        print(f"  - RELEASE_ID:        {release_id}")
        print(f"  - PAYOUT_BATCH_ID:   {payout.payout_batch_id}")
        print(f"  - REFUND_ID:         {refund.refund_id}")
        print("=" * 70)
        print(" [PASSED] ALL 4 RAILS VERIFIED WITH DETERMINISTIC IDEMPOTENCY.")
        return True

    except Exception as exc:
        print(f"\n[FAIL] Smoke test encountered an error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    provider_arg = sys.argv[1] if len(sys.argv) > 1 else None
    success = asyncio.run(run_smoke_test(provider_arg))
    sys.exit(0 if success else 1)

