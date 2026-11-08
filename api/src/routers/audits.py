import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import Audit, Evidence, Campaign, Payee, Review
from api.src.services.ledger import append_audit_log, utcnow


router = APIRouter(tags=["Audits & Reviewer Queue"])


class ReviewCreate(BaseModel):
    action: str  # APPROVE, REJECT, REQUEST_MORE
    reviewer: str
    reason: str


@router.get("/audits/{audit_id}")
async def get_audit(audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve full audit breakdown, check results, risk score, and explanation."""
    stmt = select(Audit).where(Audit.id == audit_id)
    audit = (await db.execute(stmt)).scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit record not found.")

    stmt_ev = select(Evidence).where(Evidence.id == audit.evidence_id)
    evidence = (await db.execute(stmt_ev)).scalar_one()

    return {
        "id": str(audit.id),
        "evidence_id": str(evidence.id),
        "risk_score": audit.risk_score,
        "decision": audit.decision,
        "explanation": audit.explanation,
        "checks": audit.checks_json,
        "extracted_data": evidence.extracted_json,
        "model_info": audit.model_info,
        "created_at": audit.created_at,
    }


@router.get("/reviews/queue")
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """
    Feeds the AG Grid reviewer queue table with flagged cases
    (decision in HUMAN_REVIEW, REQUEST_MORE, or REJECT).
    """
    stmt = (
        select(Audit, Evidence, Campaign, Payee)
        .join(Evidence, Audit.evidence_id == Evidence.id)
        .join(Campaign, Evidence.campaign_id == Campaign.id)
        .join(Payee, Campaign.payee_id == Payee.id)
        .where(Audit.decision.in_(["HUMAN_REVIEW", "REQUEST_MORE", "REJECT"]))
        .order_by(Audit.risk_score.desc(), Audit.created_at.desc())
    )
    results = (await db.execute(stmt)).all()

    queue_items = []
    for audit, evidence, campaign, payee in results:
        # Check if already reviewed
        stmt_rev = select(Review).where(Review.audit_id == audit.id)
        review = (await db.execute(stmt_rev)).scalar_one_or_none()

        queue_items.append({
            "audit_id": str(audit.id),
            "campaign_id": str(campaign.id),
            "campaign_title": campaign.title,
            "payee_name": payee.legal_name,
            "payee_registration_id": payee.registration_id,
            "requested_amount": evidence.requested_amount,
            "risk_score": audit.risk_score,
            "decision": audit.decision,
            "explanation": audit.explanation,
            "evidence_file_path": evidence.file_path,
            "payee_confirmed": evidence.payee_confirmed,
            "reviewed": review is not None,
            "reviewer_action": review.action if review else None,
            "created_at": audit.created_at,
        })

    return queue_items


@router.post("/reviews/{audit_id}")
async def submit_review(
    audit_id: uuid.UUID,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Human reviewer disposition for flagged evidence.
    Actions: APPROVE, REJECT, REQUEST_MORE. Mandatory reason required.
    """
    if payload.action not in ("APPROVE", "REJECT", "REQUEST_MORE"):
        raise HTTPException(status_code=400, detail="Action must be APPROVE, REJECT, or REQUEST_MORE.")
    if not payload.reason or len(payload.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Mandatory review explanation reason must be provided.")

    stmt = select(Audit).where(Audit.id == audit_id)
    audit = (await db.execute(stmt)).scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    review = Review(
        audit_id=audit.id,
        reviewer=payload.reviewer,
        action=payload.action,
        reason=payload.reason,
    )
    db.add(review)

    # Update audit decision to reflect human decision
    if payload.action == "APPROVE":
        audit.decision = "RELEASE"
    elif payload.action == "REJECT":
        audit.decision = "REJECT"
    elif payload.action == "REQUEST_MORE":
        audit.decision = "REQUEST_MORE"

    await append_audit_log(
        session=db,
        event_type="HUMAN_REVIEW_DISPOSITION",
        payload={
            "audit_id": str(audit.id),
            "reviewer": payload.reviewer,
            "action": payload.action,
            "reason": payload.reason,
            "resulting_decision": audit.decision,
        },
    )

    await db.commit()
    return {
        "audit_id": str(audit.id),
        "status": "RECORDED",
        "action": payload.action,
        "reviewer": payload.reviewer,
        "reason": payload.reason,
    }

