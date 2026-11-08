import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import (
    Payee,
    Campaign,
    Donation,
    Evidence,
    Audit,
    LedgerEntry,
    Fingerprint,
    Review,
    Refund,
    Release,
)
from api.src.services.evidence import compute_hashes
from api.src.services.auditor import run_evidence_audit
from api.src.services.ledger import append_audit_log, utcnow


router = APIRouter(prefix="/sim", tags=["Simulation & Attack Lab"])


@router.post("/seed")
async def seed_demo_environment(db: AsyncSession = Depends(get_db)):
    """
    Seeds fictional payees and active campaigns for demo and evaluation.
    Preserves database integrity and initializes clean demo state.
    """
    # Create or retrieve St. Jude Fictional
    stmt = select(Payee).where(Payee.registration_id == "REG-US-89104")
    st_jude = (await db.execute(stmt)).scalar_one_or_none()
    if not st_jude:
        st_jude = Payee(
            legal_name="St. Jude Children's Health Center (Sandbox Fictional)",
            registration_id="REG-US-89104",
            paypal_email="stjude-payee@sandbox.paypal.com",
            category="HEALTHCARE",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Seeded verified fictional hospital.",
        )
        db.add(st_jude)
        await db.flush()

    # Create or retrieve Hope Academy
    stmt2 = select(Payee).where(Payee.registration_id == "REG-EDU-44210")
    hope = (await db.execute(stmt2)).scalar_one_or_none()
    if not hope:
        hope = Payee(
            legal_name="Hope Academy STEM Foundation (Sandbox Fictional)",
            registration_id="REG-EDU-44210",
            paypal_email="hope-academy@sandbox.paypal.com",
            category="EDUCATION",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Seeded verified fictional school.",
        )
        db.add(hope)
        await db.flush()

    # Create or retrieve Metro Health
    stmt3 = select(Payee).where(Payee.registration_id == "REG-MED-12993")
    metro = (await db.execute(stmt3)).scalar_one_or_none()
    if not metro:
        metro = Payee(
            legal_name="Metro Community Clinic Fictional",
            registration_id="REG-MED-12993",
            paypal_email="metro-clinic@sandbox.paypal.com",
            category="HEALTHCARE",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Seeded verified fictional clinic.",
        )
        db.add(metro)
        await db.flush()

    # Create Active Campaign 1
    stmt_c1 = select(Campaign).where(Campaign.title == "Pediatric Cancer Treatment Support")
    c1 = (await db.execute(stmt_c1)).scalar_one_or_none()
    if not c1:
        c1 = Campaign(
            title="Pediatric Cancer Treatment Support",
            story="Direct funding for specialized pediatric radiation equipment and therapy at St. Jude.",
            purpose_category="MEDICAL",
            goal=15000.0,
            currency="USD",
            organizer="Sarah Connor",
            payee_id=st_jude.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(minutes=15),
        )
        db.add(c1)
        await db.flush()

        # Seed initial captured donation of $10,000 to have held funds available
        don = Donation(
            campaign_id=c1.id,
            donor_name="Alex River",
            donor_email="alex.donor@sandbox.vouch",
            amount=10000.0,
            paypal_order_id="mock_seed_order_01",
            paypal_capture_id="mock_seed_cap_01",
            status="CAPTURED",
            request_id="seed_req_01",
        )
        db.add(don)
        db.add(LedgerEntry(campaign_id=c1.id, type="DONATION", amount=10000.0, paypal_ref="mock_seed_cap_01", status="CONFIRMED"))

    # Ensure Campaign 1 always has active status and available held balance
    from api.src.services.ledger import compute_held
    c1_held = await compute_held(db, c1.id)
    if c1_held < 2500.0:
        c1.status = "ACTIVE"
        c1.proof_deadline = utcnow() + timedelta(minutes=15)
        topup_id = uuid.uuid4()
        db.add(Donation(
            id=topup_id,
            campaign_id=c1.id,
            donor_name="Demo Topup Donor",
            donor_email="demo.donor@sandbox.vouch",
            amount=10000.0,
            paypal_order_id=f"mock_topup_ord_{topup_id.hex[:8]}",
            paypal_capture_id=f"mock_cap_{topup_id.hex[:8]}",
            status="CAPTURED",
            request_id=f"topup_req_{topup_id.hex[:8]}",
        ))
        db.add(LedgerEntry(
            campaign_id=c1.id,
            type="DONATION",
            amount=10000.0,
            paypal_ref=f"mock_cap_{topup_id.hex[:8]}",
            status="CONFIRMED",
        ))

    stmt_c2 = select(Campaign).where(Campaign.title == "STEM Robotics Lab Equipment")
    c2 = (await db.execute(stmt_c2)).scalar_one_or_none()
    if not c2:
        c2 = Campaign(
            title="STEM Robotics Lab Equipment",
            story="Equipping high school classroom with 20x robotics kits and 3D printing equipment.",
            purpose_category="EDUCATION",
            goal=10000.0,
            currency="USD",
            organizer="Marcus Wright",
            payee_id=hope.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(minutes=15),
        )
        db.add(c2)
        await db.flush()

        don2 = Donation(
            campaign_id=c2.id,
            donor_name="Elena Rostova",
            donor_email="elena.donor@sandbox.vouch",
            amount=8000.0,
            paypal_order_id="mock_seed_order_02",
            paypal_capture_id="mock_seed_cap_02",
            status="CAPTURED",
            request_id="seed_req_02",
        )
        db.add(don2)
        db.add(LedgerEntry(campaign_id=c2.id, type="DONATION", amount=8000.0, paypal_ref="mock_seed_cap_02", status="CONFIRMED"))

    # Create Active Campaign 3 (Metro Health)
    stmt_c3 = select(Campaign).where(Campaign.title == "Clean Water & Community Clinic Supplies")
    c3 = (await db.execute(stmt_c3)).scalar_one_or_none()
    if not c3:
        c3 = Campaign(
            title="Clean Water & Community Clinic Supplies",
            story="Providing clean water filtration units and vital medical supplies for community clinic.",
            purpose_category="HEALTHCARE",
            goal=12000.0,
            currency="USD",
            organizer="David Chen",
            payee_id=metro.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(minutes=15),
        )
        db.add(c3)
        await db.flush()

        don3 = Donation(
            campaign_id=c3.id,
            donor_name="Jordan Reed",
            donor_email="jordan.donor@sandbox.vouch",
            amount=10000.0,
            paypal_order_id="mock_seed_order_03",
            paypal_capture_id="mock_seed_cap_03",
            status="CAPTURED",
            request_id="seed_req_03",
        )
        db.add(don3)
        db.add(LedgerEntry(campaign_id=c3.id, type="DONATION", amount=10000.0, paypal_ref="mock_seed_cap_03", status="CONFIRMED"))

    # Seed real CMS DMEPOS & Catalog reference prices
    from api.src.routers.reference_prices import seed_reference_prices
    await seed_reference_prices(db=db)

    await append_audit_log(
        session=db,
        event_type="ENVIRONMENT_SEEDED",
        payload={
            "st_jude_id": str(st_jude.id),
            "hope_academy_id": str(hope.id),
            "metro_health_id": str(metro.id),
            "campaign_1_id": str(c1.id),
            "campaign_2_id": str(c2.id),
            "campaign_3_id": str(c3.id),
        },
    )

    await db.commit()
    return {
        "status": "seeded",
        "payees": [
            {"id": str(st_jude.id), "name": st_jude.legal_name, "status": st_jude.status},
            {"id": str(hope.id), "name": hope.legal_name, "status": hope.status},
            {"id": str(metro.id), "name": metro.legal_name, "status": metro.status},
        ],
        "campaigns": [
            {"id": str(c1.id), "title": c1.title, "held": 10000.0},
            {"id": str(c2.id), "title": c2.title, "held": 8000.0},
            {"id": str(c3.id), "title": c3.title, "held": 10000.0},
        ],
    }


@router.post("/reset")
async def reset_demo_environment(db: AsyncSession = Depends(get_db)):
    """
    Complete hackathon demo reset:
    Clears evidence, fingerprints, audits, reviews, releases, and restores cleanly seeded environment.
    """
    # Correct FK deletion order (children before referenced parents)
    await db.execute(delete(Fingerprint))
    await db.execute(delete(Review))
    await db.execute(delete(LedgerEntry))
    await db.execute(delete(Release))
    await db.execute(delete(Refund))
    await db.execute(delete(Audit))
    await db.execute(delete(Evidence))
    await db.execute(delete(Donation))
    await db.execute(delete(Campaign))
    await db.execute(delete(Payee))
    await db.commit()

    return await seed_demo_environment(db=db)


@router.post("/attack/{kind}")
async def run_attack_simulation(kind: str, db: AsyncSession = Depends(get_db)):
    """
    Attack Lab execution: triggers a simulated attack from our 30-case dataset,
    runs the Evidence Auditor, and returns the verdict and plain-language explanation.
    """
    kind_mapping = {
        "forged_total": "case_13_fraud_forged_total_1",
        "payee_mismatch": "case_16_fraud_payee_mismatch_1",
        "inflated_price": "case_19_fraud_inflated_price_1",
        "duplicate_invoice": "case_22_fraud_duplicate_invoice_1",
        "reused_photo": "case_25_fraud_reused_photo_1",
        "altered_date": "case_28_fraud_altered_date_past",
        "prompt_injection": "case_30_fraud_prompt_injection",
    }

    if kind not in kind_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack kind. Supported: {list(kind_mapping.keys())}",
        )

    case_id = kind_mapping[kind]
    invoices_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../eval/dataset/invoices"))
    pdf_path = os.path.join(invoices_dir, f"{case_id}.pdf")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"Attack invoice file {case_id}.pdf not found.")

    # Find campaign 1 to target
    stmt = select(Campaign).order_by(Campaign.created_at.asc()).limit(1)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=400, detail="Please call /sim/seed first to initialize demo campaigns.")

    stmt_payee = select(Payee).where(Payee.id == campaign.payee_id)
    payee = (await db.execute(stmt_payee)).scalar_one()

    with open(pdf_path, "rb") as f:
        content = f.read()

    sha256, phash = compute_hashes(content, "application/pdf")

    evidence = Evidence(
        campaign_id=campaign.id,
        file_path=pdf_path,
        sha256=sha256,
        phash=phash,
        requested_amount=3000.0,
        status="PENDING",
    )
    db.add(evidence)
    await db.flush()

    audit = await run_evidence_audit(
        session=db,
        evidence=evidence,
        campaign=campaign,
        payee=payee,
    )

    detected = (audit.decision in ("REJECT", "HUMAN_REVIEW", "REQUEST_MORE"))

    return {
        "attack_kind": kind,
        "case_id": case_id,
        "audit_id": str(audit.id),
        "decision": audit.decision,
        "risk_score": audit.risk_score,
        "detected": detected,
        "explanation": audit.explanation,
        "checks_breakdown": audit.checks_json,
    }
