import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import Donation, Campaign, Payee, LedgerEntry, AuditLog, Refund, Release
from api.src.services.ledger import verify_audit_chain


router = APIRouter(tags=["Transparency & Audit Trail"])


@router.get("/receipts/{donation_id}")
async def get_donor_receipt(donation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Public transparent donor receipt showing donation details,
    the verified institutional payee, released payments, or automatic refunds.
    """
    stmt = select(Donation).where(Donation.id == donation_id)
    donation = (await db.execute(stmt)).scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    stmt_camp = select(Campaign).where(Campaign.id == donation.campaign_id)
    campaign = (await db.execute(stmt_camp)).scalar_one()

    stmt_payee = select(Payee).where(Payee.id == campaign.payee_id)
    payee = (await db.execute(stmt_payee)).scalar_one()

    # Releases associated with campaign
    stmt_rel = select(Release).where(Release.campaign_id == campaign.id)
    releases = (await db.execute(stmt_rel)).scalars().all()

    # Refund if applicable
    stmt_ref = select(Refund).where(Refund.donation_id == donation.id)
    refund = (await db.execute(stmt_ref)).scalar_one_or_none()

    # Head of audit log
    stmt_log = select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    last_log = (await db.execute(stmt_log)).scalar_one_or_none()

    return {
        "donation_id": str(donation.id),
        "campaign_id": str(campaign.id),
        "campaign_title": campaign.title,
        "donor_name": donation.donor_name,
        "amount": donation.amount,
        "currency": campaign.currency,
        "status": donation.status,
        "paypal_capture_id": donation.paypal_capture_id,
        "verified_payee": {
            "name": payee.legal_name,
            "registration_id": payee.registration_id,
            "category": payee.category,
        },
        "releases": [
            {
                "release_id": r.release_id,
                "amount": r.amount,
                "paypal_batch_id": r.paypal_batch_id,
                "released_at": r.created_at,
            }
            for r in releases
        ],
        "refund": {
            "amount": refund.amount,
            "reason": refund.reason,
            "paypal_refund_id": refund.paypal_refund_id,
            "refunded_at": refund.created_at,
        } if refund else None,
        "tamper_proof_chain_head": last_log.hash if last_log else None,
        "created_at": donation.created_at,
    }


@router.get("/audit-log")
async def get_audit_log(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Retrieve hash-chained audit log records."""
    stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(min(limit, 500))
    records = (await db.execute(stmt)).scalars().all()
    return records


@router.get("/audit-log/verify")
async def verify_chain(db: AsyncSession = Depends(get_db)):
    """
    Cryptographically verify the SHA-256 hash chain from genesis to head.
    Returns valid: true if every block link is intact.
    """
    result = await verify_audit_chain(db)
    return result
