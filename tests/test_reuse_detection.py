import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.src.main import app


@pytest.mark.asyncio
async def test_reuse_detection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed the database
        seed_resp = await client.post("/sim/seed")
        assert seed_resp.status_code == 200
        seed_data = seed_resp.json()
        c1_id = seed_data["campaigns"][0]["id"]
        c2_id = seed_data["campaigns"][1]["id"]

        # Upload Case 01 invoice to Campaign 1
        test_invoice_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../eval/dataset/invoices/case_01_legit_surgery.pdf")
        )
        with open(test_invoice_path, "rb") as f:
            ev1_resp = await client.post(
                f"/campaigns/{c1_id}/evidence",
                data={"requested_amount": "8500.00"},
                files={"file": ("case_01.pdf", f, "application/pdf")},
            )
        assert ev1_resp.status_code == 202

        # Now attempt to upload the DUPLICATE invoice (Case 22 has identical invoice number and items) to Campaign 2!
        dup_invoice_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../eval/dataset/invoices/case_22_fraud_duplicate_invoice_1.pdf")
        )
        with open(dup_invoice_path, "rb") as f:
            ev2_resp = await client.post(
                f"/campaigns/{c2_id}/evidence",
                data={"requested_amount": "8500.00"},
                files={"file": ("case_22_dup.pdf", f, "application/pdf")},
            )
        assert ev2_resp.status_code == 202
        ev2_data = ev2_resp.json()

        # Hard Check H5 must fail -> Decision must be REJECT!
        assert ev2_data["decision"] == "REJECT"
        assert "already submitted to another campaign" in ev2_data["explanation"]
