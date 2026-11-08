import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import Campaign, Payee, Donation, Evidence, LedgerEntry, Milestone, Audit
from api.src.services.payment.factory import get_payment_provider
from api.src.services.evidence import validate_file_content, compute_hashes, save_upload_file
from api.src.services.auditor import run_evidence_audit
from api.src.services.ledger import compute_held, get_campaign_financials, append_audit_log, utcnow


router = APIRouter(tags=["Campaigns"])


class MilestoneCreate(BaseModel):
    title: str
    target_amount: float


class CampaignCreate(BaseModel):
    title: str
    story: str
    purpose_category: str
    goal: float
    currency: str = "USD"
    organizer: str
    payee_id: uuid.UUID
    milestones: Optional[List[MilestoneCreate]] = None
    proof_deadline_minutes: int = 3  # 3 minutes for hackathon demo


class DonationCreate(BaseModel):
    donor_name: str
    donor_email: EmailStr
    amount: float


@router.get("/campaigns")
async def list_campaigns(status_filter: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List all campaigns with optional status filter."""
    stmt = select(Campaign)
    if status_filter:
        stmt = stmt.where(Campaign.status == status_filter.upper())
    stmt = stmt.order_by(Campaign.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    """Create a campaign. F1 rule: campaign cannot be created/active unless payee is VERIFIED."""
    stmt = select(Payee).where(Payee.id == payload.payee_id)
    payee = (await db.execute(stmt)).scalar_one_or_none()
    if not payee:
        raise HTTPException(status_code=404, detail="Designated payee not found.")

    if payee.status != "VERIFIED":
        raise HTTPException(
            status_code=400,
            detail=f"F1 Invariant: Campaign payee must be VERIFIED before campaign creation. Current status: {payee.status}.",
        )

    deadline = utcnow() + timedelta(minutes=payload.proof_deadline_minutes)

    campaign = Campaign(
        title=payload.title,
        story=payload.story,
        purpose_category=payload.purpose_category,
        goal=payload.goal,
        currency=payload.currency.upper(),
        organizer=payload.organizer,
        payee_id=payload.payee_id,
        status="ACTIVE",
        proof_deadline=deadline,
    )
    db.add(campaign)
    await db.flush()

    if payload.milestones:
        for ms in payload.milestones:
            db.add(Milestone(campaign_id=campaign.id, title=ms.title, target_amount=ms.target_amount))

    await append_audit_log(
        session=db,
        event_type="CAMPAIGN_CREATED",
        payload={
            "campaign_id": str(campaign.id),
            "title": campaign.title,
            "goal": campaign.goal,
            "payee_id": str(payee.id),
            "proof_deadline": deadline.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve campaign details with associated payee and held balance."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    stmt_payee = select(Payee).where(Payee.id == campaign.payee_id)
    payee = (await db.execute(stmt_payee)).scalar_one_or_none()

    fin = await get_campaign_financials(db, campaign.id)

    return {
        "id": str(campaign.id),
        "title": campaign.title,
        "story": campaign.story,
        "purpose_category": campaign.purpose_category,
        "goal": campaign.goal,
        "currency": campaign.currency,
        "organizer": campaign.organizer,
        "status": campaign.status,
        "proof_deadline": campaign.proof_deadline,
        "created_at": campaign.created_at,
        "payee": payee,
        "financials": fin,
    }


@router.post("/campaigns/{campaign_id}/donate", status_code=status.HTTP_201_CREATED)
async def donate_to_campaign(
    campaign_id: uuid.UUID,
    payload: DonationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate donation via PayPal Orders v2.
    Records Donation in INITIATED state with custom_id = donation_id.
    """
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if campaign.status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Cannot donate to campaign in {campaign.status} status.")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Donation amount must be greater than zero.")

    donation_id = uuid.uuid4()
    req_id = f"ord_req_{donation_id.hex[:12]}"

    provider = get_payment_provider()
    order_result = await provider.create_order(
        donation_id=str(donation_id),
        amount=payload.amount,
        currency=campaign.currency,
        request_id=req_id,
    )

    donation = Donation(
        id=donation_id,
        campaign_id=campaign.id,
        donor_name=payload.donor_name,
        donor_email=str(payload.donor_email),
        amount=payload.amount,
        paypal_order_id=order_result.order_id,
        status="INITIATED",
        request_id=req_id,
    )
    db.add(donation)
    await db.commit()

    return {
        "donation_id": str(donation.id),
        "paypal_order_id": order_result.order_id,
        "approve_url": order_result.approve_url,
        "status": donation.status,
    }


@router.post("/orders/{order_id}/capture")
async def capture_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """
    Capture approved PayPal order into platform account.
    F2 rule: row-level lock on Campaign with with_for_update(), writes LedgerEntry DONATION (HELD),
    and appends to hash-chained audit log in the same database transaction.
    """
    stmt = select(Donation).where(Donation.paypal_order_id == order_id)
    donation = (await db.execute(stmt)).scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record for order not found.")

    if donation.status == "CAPTURED":
        return donation

    # Row-level lock on campaign to guarantee serialized concurrency
    stmt_camp = select(Campaign).where(Campaign.id == donation.campaign_id).with_for_update()
    campaign = (await db.execute(stmt_camp)).scalar_one()

    provider = get_payment_provider()
    capture_req_id = f"cap_req_{donation.id.hex[:12]}"
    capture_res = await provider.capture_order(order_id=order_id, request_id=capture_req_id)

    donation.paypal_capture_id = capture_res.capture_id
    donation.status = "CAPTURED"

    # Insert DONATION ledger entry
    ledger_entry = LedgerEntry(
        campaign_id=campaign.id,
        type="DONATION",
        amount=donation.amount,
        paypal_ref=capture_res.capture_id,
        status="CONFIRMED",
    )
    db.add(ledger_entry)

    # Append to cryptographic audit log
    await append_audit_log(
        session=db,
        event_type="DONATION_CAPTURED_AND_HELD",
        payload={
            "donation_id": str(donation.id),
            "campaign_id": str(campaign.id),
            "amount": donation.amount,
            "paypal_capture_id": capture_res.capture_id,
            "status": "HELD",
        },
    )

    await db.commit()
    await db.refresh(donation)
    return donation


@router.post("/campaigns/{campaign_id}/evidence", status_code=status.HTTP_202_ACCEPTED)
async def upload_evidence(
    campaign_id: uuid.UUID,
    file: UploadFile = File(...),
    requested_amount: float = Form(...),
    milestone_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload spend evidence document (PDF/JPG/PNG <= 10MB).
    Computes SHA-256 and pHash, registers confirmation token, and runs Evidence Auditor.
    """
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    stmt_payee = select(Payee).where(Payee.id == campaign.payee_id)
    payee = (await db.execute(stmt_payee)).scalar_one()

    # Read and validate file content
    content = await file.read()
    mime_type = validate_file_content(content, file.content_type or "")
    sha256, phash = compute_hashes(content, mime_type)
    saved_path = save_upload_file(content, mime_type)

    evidence = Evidence(
        campaign_id=campaign.id,
        file_path=saved_path,
        sha256=sha256,
        phash=phash,
        requested_amount=requested_amount,
        status="PENDING",
    )
    db.add(evidence)
    await db.flush()

    # Run Evidence Auditor
    audit = await run_evidence_audit(
        session=db,
        evidence=evidence,
        campaign=campaign,
        payee=payee,
    )

    await append_audit_log(
        session=db,
        event_type="EVIDENCE_AUDITED",
        payload={
            "evidence_id": str(evidence.id),
            "campaign_id": str(campaign.id),
            "sha256": sha256,
            "decision": audit.decision,
            "risk_score": audit.risk_score,
            "explanation": audit.explanation,
        },
    )

    await db.commit()

    return {
        "evidence_id": str(evidence.id),
        "audit_id": str(audit.id),
        "sha256": sha256,
        "phash": phash,
        "requested_amount": requested_amount,
        "decision": audit.decision,
        "risk_score": audit.risk_score,
        "explanation": audit.explanation,
        "confirmation_token": evidence.confirmation_token,
    }


@router.get("/campaigns/{campaign_id}/ledger")
async def get_ledger(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve financial ledger and itemized transaction entries."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    fin = await get_campaign_financials(db, campaign.id)

    stmt_entries = (
        select(LedgerEntry)
        .where(LedgerEntry.campaign_id == campaign.id)
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = (await db.execute(stmt_entries)).scalars().all()

    return {
        "campaign_id": str(campaign.id),
        "financials": fin,
        "entries": entries,
    }

