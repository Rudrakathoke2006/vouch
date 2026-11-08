import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.src.main import app
from api.src.services.payment.factory import reset_payment_provider


@pytest.fixture(autouse=True)
def setup_mock_env():
    os.environ["PAYMENT_PROVIDER"] = "mock"
    os.environ["LLM_PROVIDER"] = "mock"
    reset_payment_provider()


@pytest.mark.asyncio
async def test_complete_day2_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # 1. Register institutional payee
        reg_id = f"REG-TEST-{uuid.uuid4().hex[:6]}"
        payee_resp = await client.post(
            "/payees",
            json={
                "legal_name": "Mercy Children's Hospital (Sandbox)",
                "registration_id": reg_id,
                "paypal_email": "mercy-hospital@sandbox.paypal.com",
                "category": "HEALTHCARE",
            },
        )
        assert payee_resp.status_code == 201, payee_resp.text
        payee_data = payee_resp.json()
        payee_id = payee_data["id"]
        assert payee_data["status"] == "PENDING"

        # 2. Invariant F1: Campaign creation fails if payee is PENDING
        failed_camp = await client.post(
            "/campaigns",
            json={
                "title": "Unverified Payee Campaign",
                "story": "This campaign should be blocked until payee is verified.",
                "purpose_category": "MEDICAL",
                "goal": 5000.0,
                "currency": "USD",
                "organizer": "Test Organizer",
                "payee_id": payee_id,
                "proof_deadline_minutes": 3,
            },
        )
        assert failed_camp.status_code == 400
        assert "must be VERIFIED" in failed_camp.json()["detail"]

        # 3. Verify payee
        verify_resp = await client.post(
            f"/payees/{payee_id}/verify",
            json={
                "status": "VERIFIED",
                "verified_by": "reviewer_sarah",
                "notes": "Verified against state registry.",
            },
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "VERIFIED"

        # 4. Create campaign with VERIFIED payee
        camp_resp = await client.post(
            "/campaigns",
            json={
                "title": "Mercy Pediatric Emergency Care",
                "story": "Funding critical care and pediatric surgery equipment.",
                "purpose_category": "MEDICAL",
                "goal": 8500.0,
                "currency": "USD",
                "organizer": "Sarah Connor",
                "payee_id": payee_id,
                "proof_deadline_minutes": 5,
            },
        )
        assert camp_resp.status_code == 201
        camp_data = camp_resp.json()
        camp_id = camp_data["id"]

        # 5. Donate to campaign
        donate_resp = await client.post(
            f"/campaigns/{camp_id}/donate",
            json={
                "donor_name": "John Doe",
                "donor_email": "john.donor@example.com",
                "amount": 2500.0,
            },
        )
        assert donate_resp.status_code == 201
        don_data = donate_resp.json()
        order_id = don_data["paypal_order_id"]
        donation_id = don_data["donation_id"]

        # 6. Capture donation (holds funds in platform account)
        cap_resp = await client.post(f"/orders/{order_id}/capture")
        assert cap_resp.status_code == 200
        assert cap_resp.json()["status"] == "CAPTURED"

        # Check campaign ledger shows $2500 held
        ledger_resp = await client.get(f"/campaigns/{camp_id}/ledger")
        assert ledger_resp.status_code == 200
        ledger_data = ledger_resp.json()
        assert ledger_data["financials"]["held_balance"] == 2500.0
        assert ledger_data["financials"]["total_donations"] == 2500.0

        # 7. Upload synthetic legitimate invoice
        test_invoice_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../eval/dataset/invoices/case_01_legit_surgery.pdf")
        )
        with open(test_invoice_path, "rb") as f:
            evidence_resp = await client.post(
                f"/campaigns/{camp_id}/evidence",
                data={"requested_amount": "2500.00"},
                files={"file": ("case_01_legit_surgery.pdf", f, "application/pdf")},
            )
        assert evidence_resp.status_code == 202, evidence_resp.text
        ev_data = evidence_resp.json()
        assert "evidence_id" in ev_data
        assert "audit_id" in ev_data
        assert "sha256" in ev_data
        assert "confirmation_token" in ev_data

        # 8. Add-on 1: Payee independently confirms the invoice
        confirm_token = ev_data["confirmation_token"]
        confirm_resp = await client.post(
            f"/payees/{payee_id}/confirm-evidence/{confirm_token}",
            json={
                "confirmed": True,
                "signer_name": "Chief Medical Officer Dr. Vance",
                "notes": "Confirmed this invoice was issued for trauma surgery.",
            },
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["payee_confirmed"] is True

        # 9. Verify Public Donor Receipt
        receipt_resp = await client.get(f"/receipts/{donation_id}")
        assert receipt_resp.status_code == 200
        receipt = receipt_resp.json()
        assert receipt["donor_name"] == "John Doe"
        assert receipt["amount"] == 2500.0
        assert receipt["status"] == "CAPTURED"
        assert receipt["verified_payee"]["registration_id"] == reg_id
        assert receipt["tamper_proof_chain_head"] is not None

        # 10. Cryptographically verify the hash chain
        chain_verify_resp = await client.get("/audit-log/verify")
        assert chain_verify_resp.status_code == 200
        chain_result = chain_verify_resp.json()
        assert chain_result["valid"] is True
        assert chain_result["total_entries"] >= 4
        assert chain_result["error"] is None
