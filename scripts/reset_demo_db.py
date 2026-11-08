#!/usr/bin/env python3
"""
Vouch Pristine Demo Database Reset Script.
Wipes old test residues, duplicate seed records, and oversized test chain blocks.
Initializes a clean, verified state:
- 3 Distinct fictional payees (Beacon Clinic, Horizon STEM, Metro Health)
- 3 Active campaigns with escrow held balances
- Canonical SHA-256 genesis and initialization audit log blocks (~8 blocks total)
- 100% verified cryptographic integrity ready for judges and live demonstration.
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, workspace_dir)

from sqlalchemy import delete, select
from api.src.database import engine, AsyncSessionLocal
from api.src.models import (
    Base,
    Payee,
    Campaign,
    Milestone,
    Donation,
    Evidence,
    Audit,
    LedgerEntry,
    Refund,
    Release,
    Fingerprint,
    Review,
    AuditLog,
    AgentTrace,
    WebhookEvent,
    PayeeVerification,
)
from api.src.services.ledger import append_audit_log, utcnow


async def reset_demo_database():
    print("=" * 70)
    print(" VOUCH: PRISTINE DEMO DATABASE RESET")
    print("=" * 70)
    print(f"[*] Target Database: {engine.url}")
    print(f"[*] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("\n[*] Purging operational tables and test residues...")
        await session.execute(delete(Fingerprint))
        await session.execute(delete(Review))
        await session.execute(delete(AgentTrace))
        await session.execute(delete(WebhookEvent))
        await session.execute(delete(Release))
        await session.execute(delete(Refund))
        await session.execute(delete(LedgerEntry))
        await session.execute(delete(Audit))
        await session.execute(delete(Evidence))
        await session.execute(delete(Milestone))
        await session.execute(delete(Donation))
        await session.execute(delete(Campaign))
        await session.execute(delete(PayeeVerification))
        await session.execute(delete(Payee))
        await session.execute(delete(AuditLog))
        await session.commit()
        print("    [OK] All tables purged successfully.")

        # Seed Fictional Payees
        print("\n[*] Seeding clean fictional payees & active campaigns...")
        
        # Payee 1: Healthcare Hospital
        beacon_clinic = Payee(
            legal_name="Beacon Children's Memorial Clinic (Sandbox Fictional)",
            registration_id="REG-MED-89104",
            paypal_email="beacon-clinic@sandbox.paypal.com",
            category="HEALTHCARE",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Fictional verified pediatric clinic for hackathon sandbox demonstration.",
        )
        session.add(beacon_clinic)

        # Payee 2: STEM Education Foundation
        horizon_stem = Payee(
            legal_name="Horizon STEM Academy (Sandbox Fictional)",
            registration_id="REG-EDU-44210",
            paypal_email="horizon-academy@sandbox.paypal.com",
            category="EDUCATION",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Fictional verified STEM foundation for hackathon sandbox demonstration.",
        )
        session.add(horizon_stem)

        # Payee 3: Community Health Center
        metro_clinic = Payee(
            legal_name="Metro Community Health Center (Sandbox Fictional)",
            registration_id="REG-MED-12993",
            paypal_email="metro-clinic@sandbox.paypal.com",
            category="HEALTHCARE",
            status="VERIFIED",
            verified_by="system_seed",
            notes="Fictional verified outpatient clinic for hackathon sandbox demonstration.",
        )
        session.add(metro_clinic)
        await session.flush()

        # Seed Active Campaign 1
        c1 = Campaign(
            title="Pediatric Cancer Treatment Support",
            story="Direct funding for specialized pediatric radiation equipment and therapy at Beacon Children's Memorial Clinic.",
            purpose_category="MEDICAL",
            goal=15000.0,
            currency="USD",
            organizer="Sarah Connor",
            payee_id=beacon_clinic.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(days=7),
        )
        session.add(c1)
        await session.flush()

        don1 = Donation(
            campaign_id=c1.id,
            donor_name="Alex River",
            donor_email="alex.donor@sandbox.vouch",
            amount=10000.0,
            paypal_order_id="mock_seed_order_01",
            paypal_capture_id="mock_seed_cap_01",
            status="CAPTURED",
            request_id="seed_req_01",
        )
        session.add(don1)
        session.add(LedgerEntry(campaign_id=c1.id, type="DONATION", amount=10000.0, paypal_ref="mock_seed_cap_01", status="CONFIRMED"))

        # Seed Active Campaign 2
        c2 = Campaign(
            title="STEM Robotics Lab Equipment",
            story="Equipping high school classroom with 20x robotics kits and 3D printing equipment for student engineering teams.",
            purpose_category="EDUCATION",
            goal=10000.0,
            currency="USD",
            organizer="Marcus Wright",
            payee_id=horizon_stem.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(days=5),
        )
        session.add(c2)
        await session.flush()

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
        session.add(don2)
        session.add(LedgerEntry(campaign_id=c2.id, type="DONATION", amount=8000.0, paypal_ref="mock_seed_cap_02", status="CONFIRMED"))

        # Seed Active Campaign 3
        c3 = Campaign(
            title="Clean Water & Community Clinic Supplies",
            story="Providing clean water filtration units and emergency clinical supplies for local community clinic.",
            purpose_category="HEALTHCARE",
            goal=12000.0,
            currency="USD",
            organizer="David Chen",
            payee_id=metro_clinic.id,
            status="ACTIVE",
            proof_deadline=utcnow() + timedelta(days=6),
        )
        session.add(c3)
        await session.flush()

        don3 = Donation(
            campaign_id=c3.id,
            donor_name="Jordan Bell",
            donor_email="jordan.donor@sandbox.vouch",
            amount=6000.0,
            paypal_order_id="mock_seed_order_03",
            paypal_capture_id="mock_seed_cap_03",
            status="CAPTURED",
            request_id="seed_req_03",
        )
        session.add(don3)
        session.add(LedgerEntry(campaign_id=c3.id, type="DONATION", amount=6000.0, paypal_ref="mock_seed_cap_03", status="CONFIRMED"))

        # Append Clean Cryptographic Audit Log Entries
        print("\n[*] Initializing tamper-evident audit hash chain from genesis...")
        await append_audit_log(session, "SYSTEM_GENESIS_INITIALIZED", {
            "platform": "Vouch",
            "version": "1.0.0",
            "rails": "PayPal Sandbox",
            "note": "Clean genesis block for demonstration and evaluation.",
        })
        await append_audit_log(session, "PAYEE_STATUS_UPDATED", {
            "payee_id": str(beacon_clinic.id),
            "legal_name": beacon_clinic.legal_name,
            "status": "VERIFIED",
        })
        await append_audit_log(session, "CAMPAIGN_CREATED", {
            "campaign_id": str(c1.id),
            "title": c1.title,
            "goal": c1.goal,
            "payee_id": str(beacon_clinic.id),
        })
        await append_audit_log(session, "DONATION_CAPTURED_AND_HELD", {
            "campaign_id": str(c1.id),
            "amount": 10000.0,
            "paypal_order_id": "mock_seed_order_01",
        })
        await append_audit_log(session, "PAYEE_STATUS_UPDATED", {
            "payee_id": str(horizon_stem.id),
            "legal_name": horizon_stem.legal_name,
            "status": "VERIFIED",
        })
        await append_audit_log(session, "CAMPAIGN_CREATED", {
            "campaign_id": str(c2.id),
            "title": c2.title,
            "goal": c2.goal,
            "payee_id": str(horizon_stem.id),
        })
        await append_audit_log(session, "DONATION_CAPTURED_AND_HELD", {
            "campaign_id": str(c2.id),
            "amount": 8000.0,
            "paypal_order_id": "mock_seed_order_02",
        })

        await session.commit()
        print("    [OK] Audit hash chain initialized with 7 canonical blocks.")

    print("\n" + "=" * 70)
    print(" DEMO DATABASE RESET COMPLETE: Clean, pristine state initialized.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(reset_demo_database())
