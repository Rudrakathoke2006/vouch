import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, update
from api.src.main import app
from api.src.database import AsyncSessionLocal
from api.src.models import Campaign, Donation, Payee, Evidence, Audit, LedgerEntry, Release, Refund
from api.src.services.payment.factory import reset_payment_provider
from api.src.services.release import execute_release_payout
from api.src.services.sweeper import run_deadline_sweeper
from api.src.services.ledger import compute_held, InvariantViolationError


@pytest.fixture(autouse=True)
def setup_mock_env():
    os.environ["PAYMENT_PROVIDER"] = "mock"
    os.environ["LLM_PROVIDER"] = "mock"
    reset_payment_provider()


@pytest.mark.asyncio
async def test_release_payout_and_invariants():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed test campaign and payee
        seed_resp = await client.post("/sim/seed")
        assert seed_resp.status_code == 200
        seed_data = seed_resp.json()
        camp_id = uuid.UUID(seed_data["campaigns"][0]["id"])

        # Upload a legitimate invoice
        test_invoice_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../eval/dataset/invoices/case_01_legit_surgery.pdf")
        )
        with open(test_invoice_path, "rb") as f:
            ev_resp = await client.post(
                f"/campaigns/{camp_id}/evidence",
                data={"requested_amount": "2500.00"},
                files={"file": ("case_01.pdf", f, "application/pdf")},
            )
        assert ev_resp.status_code == 202
        audit_id = uuid.UUID(ev_resp.json()["audit_id"])

        # Force audit decision to RELEASE for this test
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Audit).where(Audit.id == audit_id).values(decision="RELEASE")
            )
            await session.commit()

            # Execute Release
            release = await execute_release_payout(session, audit_id)
            assert release.amount == 2500.0
            assert release.paypal_batch_id.startswith("mock_batch_")

            # Check Ledger has RELEASE entry for this audit
            stmt_ledger = (
                select(LedgerEntry)
                .where(LedgerEntry.audit_id == audit_id)
                .where(LedgerEntry.type == "RELEASE")
            )
            ledger_entry = (await session.execute(stmt_ledger)).scalar_one()
            assert ledger_entry.amount == 2500.0


            # Invariant 1: Held balance can never be negative, and reflects releases
            held = await compute_held(session, camp_id)
            assert held >= 0.0


            # Re-running release for same audit must return existing release (idempotency)
            rel_dup = await execute_release_payout(session, audit_id)
            assert rel_dup.id == release.id


@pytest.mark.asyncio
async def test_deadline_sweeper_automatic_refund():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed test data
        await client.post("/sim/seed")

        async with AsyncSessionLocal() as session:
            # Find an active campaign and set its proof deadline to 1 hour in the past
            stmt = select(Campaign).where(Campaign.status == "ACTIVE").limit(1)
            camp = (await session.execute(stmt)).scalar_one()
            camp.proof_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()
            camp_id = camp.id

        # Trigger Deadline Sweeper
        tick_resp = await client.post("/admin/tick")
        assert tick_resp.status_code == 200
        summary = tick_resp.json()
        assert summary["swept_campaigns"] >= 1
        assert summary["refunds_issued"] >= 1
        assert summary["total_refunded_amount"] > 0

        # Check campaign status is now CLOSED and donations are REFUNDED
        async with AsyncSessionLocal() as session:
            stmt_c = select(Campaign).where(Campaign.id == camp_id)
            closed_camp = (await session.execute(stmt_c)).scalar_one()
            assert closed_camp.status == "CLOSED"

            stmt_don = select(Donation).where(Donation.campaign_id == camp_id)
            donations = (await session.execute(stmt_don)).scalars().all()
            for d in donations:
                assert d.status == "REFUNDED"

            # Invariant check: re-running sweeper does not double-refund!
            tick_repeat = await run_deadline_sweeper(session)
            assert tick_repeat["refunds_issued"] == 0


@pytest.mark.asyncio
async def test_webhook_verification_and_reconcile():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid webhook accepted
        event_id = f"evt_test_{uuid.uuid4().hex[:8]}"
        wh_resp = await client.post(
            "/webhooks/paypal",
            headers={
                "PAYPAL-TRANSMISSION-ID": "tx_123",
                "PAYPAL-TRANSMISSION-TIME": "2026-11-08T12:00:00Z",
                "PAYPAL-TRANSMISSION-SIG": "VALID_MOCK_SIG",
                "PAYPAL-CERT-URL": "https://api.sandbox.paypal.com/certs",
                "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            },
            json={
                "id": event_id,
                "event_type": "CHECKOUT.ORDER.APPROVED",
                "resource": {"order_id": "mock_ord_wh"},
            },
        )
        assert wh_resp.status_code == 200
        assert wh_resp.json()["status"] == "accepted"

        # 2. Duplicate webhook event ID handled idempotently
        wh_dup_resp = await client.post(
            "/webhooks/paypal",
            headers={
                "PAYPAL-TRANSMISSION-ID": "tx_123",
                "PAYPAL-TRANSMISSION-TIME": "2026-11-08T12:00:00Z",
                "PAYPAL-TRANSMISSION-SIG": "VALID_MOCK_SIG",
                "PAYPAL-CERT-URL": "https://api.sandbox.paypal.com/certs",
                "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            },
            json={
                "id": event_id,
                "event_type": "CHECKOUT.ORDER.APPROVED",
                "resource": {"order_id": "mock_ord_wh"},
            },
        )
        assert wh_dup_resp.status_code == 200
        assert wh_dup_resp.json()["status"] == "already_processed"

        # 3. Invalid signature rejected
        wh_invalid = await client.post(
            "/webhooks/paypal",
            headers={"PAYPAL-TRANSMISSION-SIG": "INVALID"},
            json={"id": "evt_invalid"},
        )
        assert wh_invalid.status_code == 400

        # 4. Reconcile endpoint
        rec_resp = await client.post("/admin/reconcile")
        assert rec_resp.status_code == 200
        assert "reconciled_count" in rec_resp.json()


@pytest.mark.asyncio
async def test_release_agent_trace():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed environment
        seed_resp = await client.post("/sim/seed")
        c1_id = seed_resp.json()["campaigns"][0]["id"]

        # Upload an invoice
        test_invoice_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../eval/dataset/invoices/case_01_legit_surgery.pdf")
        )
        with open(test_invoice_path, "rb") as f:
            ev_resp = await client.post(
                f"/campaigns/{c1_id}/evidence",
                data={"requested_amount": "1500.00"},
                files={"file": ("case_01.pdf", f, "application/pdf")},
            )
        audit_id = ev_resp.json()["audit_id"]

        # Run the Release Agent for this case
        agent_resp = await client.post(f"/audits/{audit_id}/run-agent")
        assert agent_resp.status_code == 200
        agent_data = agent_resp.json()
        assert agent_data["status"] == "COMPLETED"
        assert len(agent_data["traces"]) == 5

        # Check step sequence: get_ledger -> run_checks -> decide -> act -> explain
        tools_called = [t["tool"] for t in agent_data["traces"]]
        assert "get_ledger" in tools_called
        assert "run_checks" in tools_called
        assert "decide" in tools_called
        assert "explain_decision" in tools_called

        # Verify trace can be retrieved via GET endpoint
        trace_get_resp = await client.get(f"/audits/{audit_id}/trace")
        assert trace_get_resp.status_code == 200
        assert len(trace_get_resp.json()) == 5
