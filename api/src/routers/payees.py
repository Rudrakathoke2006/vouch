import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import Payee, Evidence
from api.src.services.ledger import append_audit_log, utcnow


router = APIRouter(prefix="/payees", tags=["Payees"])


class PayeeCreate(BaseModel):
    legal_name: str
    registration_id: str
    paypal_email: EmailStr
    category: str


class PayeeVerifyRequest(BaseModel):
    status: str  # VERIFIED or BLOCKED
    verified_by: str
    notes: Optional[str] = None


class PayeeConfirmEvidenceRequest(BaseModel):
    confirmed: bool
    signer_name: Optional[str] = None
    notes: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payee(payload: PayeeCreate, db: AsyncSession = Depends(get_db)):
    """Register a new institutional payee (default status: PENDING)."""
    # Check if registration_id already exists
    stmt = select(Payee).where(Payee.registration_id == payload.registration_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payee with registration ID {payload.registration_id} already exists.",
        )

    payee = Payee(
        legal_name=payload.legal_name,
        registration_id=payload.registration_id,
        paypal_email=str(payload.paypal_email),
        category=payload.category,
        status="PENDING",
    )
    db.add(payee)
    await db.commit()
    await db.refresh(payee)
    return payee


@router.post("/{payee_id}/verify")
async def verify_payee(
    payee_id: uuid.UUID,
    payload: PayeeVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reviewer action to verify or block an institutional payee."""
    if payload.status not in ("VERIFIED", "BLOCKED"):
        raise HTTPException(status_code=400, detail="Status must be VERIFIED or BLOCKED.")

    stmt = select(Payee).where(Payee.id == payee_id)
    payee = (await db.execute(stmt)).scalar_one_or_none()
    if not payee:
        raise HTTPException(status_code=404, detail="Payee not found.")

    payee.status = payload.status
    payee.verified_by = payload.verified_by
    payee.notes = payload.notes

    # Append to hash-chained audit log
    await append_audit_log(
        session=db,
        event_type="PAYEE_STATUS_UPDATED",
        payload={
            "payee_id": str(payee.id),
            "legal_name": payee.legal_name,
            "status": payee.status,
            "verified_by": payee.verified_by,
        },
    )

    await db.commit()
    await db.refresh(payee)
    return payee


@router.post("/{payee_id}/confirm-evidence/{token}")
async def confirm_evidence_by_payee(
    payee_id: uuid.UUID,
    token: str,
    payload: PayeeConfirmEvidenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """(Add-on 1) Payee independent confirmation that an uploaded invoice is authentic."""
    stmt = select(Evidence).where(Evidence.confirmation_token == token)
    evidence = (await db.execute(stmt)).scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Invalid or expired confirmation token.")

    evidence.payee_confirmed = payload.confirmed
    evidence.payee_confirmed_at = utcnow()
    evidence.payee_notes = payload.notes

    await append_audit_log(
        session=db,
        event_type="PAYEE_INVOICE_CONFIRMED",
        payload={
            "evidence_id": str(evidence.id),
            "payee_id": str(payee_id),
            "confirmed": payload.confirmed,
            "signer_name": payload.signer_name,
        },
    )

    await db.commit()
    return {
        "evidence_id": str(evidence.id),
        "payee_confirmed": evidence.payee_confirmed,
        "confirmed_at": evidence.payee_confirmed_at,
    }
