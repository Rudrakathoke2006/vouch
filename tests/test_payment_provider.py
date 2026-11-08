import pytest
import uuid
from api.src.services.payment.mock import MockPaymentProvider, MockPaymentError


@pytest.fixture
def mock_provider():
    provider = MockPaymentProvider()
    provider.reset()
    return provider


@pytest.mark.asyncio
async def test_order_creation_and_idempotency(mock_provider):
    donation_id = str(uuid.uuid4())
    req_id = "req_order_123"
    
    order1 = await mock_provider.create_order(
        donation_id=donation_id,
        amount=50.0,
        currency="USD",
        request_id=req_id,
    )
    assert order1.status == "CREATED"
    assert order1.amount == 50.0
    assert order1.custom_id == donation_id

    # Second call with same request_id must return the identical order
    order2 = await mock_provider.create_order(
        donation_id=donation_id,
        amount=50.0,
        currency="USD",
        request_id=req_id,
    )
    assert order2.order_id == order1.order_id
    assert order2.raw_response == order1.raw_response


@pytest.mark.asyncio
async def test_order_negative_amount_rejected(mock_provider):
    with pytest.raises(ValueError, match="must be positive"):
        await mock_provider.create_order(donation_id="d1", amount=-10.0)


@pytest.mark.asyncio
async def test_capture_and_idempotency(mock_provider):
    donation_id = str(uuid.uuid4())
    order = await mock_provider.create_order(donation_id=donation_id, amount=100.0)
    
    cap_req_id = "req_cap_456"
    cap1 = await mock_provider.capture_order(order_id=order.order_id, request_id=cap_req_id)
    assert cap1.status == "COMPLETED"
    assert cap1.amount == 100.0

    # Repeat capture call with same request_id
    cap2 = await mock_provider.capture_order(order_id=order.order_id, request_id=cap_req_id)
    assert cap2.capture_id == cap1.capture_id


@pytest.mark.asyncio
async def test_payout_and_idempotency(mock_provider):
    release_id = str(uuid.uuid4())
    payout1 = await mock_provider.create_payout(
        release_id=release_id,
        receiver_email="payee@sandbox.org",
        amount=75.0,
    )
    assert payout1.status == "SUCCESS"
    assert payout1.sender_batch_id == release_id

    # Duplicate call with same release_id
    payout2 = await mock_provider.create_payout(
        release_id=release_id,
        receiver_email="payee@sandbox.org",
        amount=75.0,
    )
    assert payout2.payout_batch_id == payout1.payout_batch_id


@pytest.mark.asyncio
async def test_refund_single_refund_invariant(mock_provider):
    order = await mock_provider.create_order(donation_id="d_refund_test", amount=80.0)
    capture = await mock_provider.capture_order(order_id=order.order_id)

    # First refund succeeds
    ref1 = await mock_provider.refund_capture(
        capture_id=capture.capture_id,
        amount=80.0,
        request_id="ref_req_1",
    )
    assert ref1.status == "COMPLETED"

    # Idempotent re-submission with same request_id returns existing refund
    ref1_idemp = await mock_provider.refund_capture(
        capture_id=capture.capture_id,
        amount=80.0,
        request_id="ref_req_1",
    )
    assert ref1_idemp.refund_id == ref1.refund_id

    # Second refund attempt with new request_id fails with duplicate refund error
    with pytest.raises(MockPaymentError, match="already refunded"):
        await mock_provider.refund_capture(
            capture_id=capture.capture_id,
            amount=80.0,
            request_id="ref_req_2",
        )


@pytest.mark.asyncio
async def test_simulated_failures(mock_provider):
    failing_provider = MockPaymentProvider(simulate_timeout=True)
    with pytest.raises(MockPaymentError, match="MockTimeoutError"):
        await failing_provider.create_order(donation_id="d2", amount=20.0)

    denied_payout_provider = MockPaymentProvider(simulate_payout_denied=True)
    with pytest.raises(MockPaymentError, match="MockPayoutDenied"):
        await denied_payout_provider.create_payout(
            release_id="rel_denied",
            receiver_email="test@hospital.org",
            amount=50.0,
        )

