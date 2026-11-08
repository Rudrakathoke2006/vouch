import uuid
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models import (
    Campaign,
    Payee,
    Evidence,
    Audit,
    Release,
    LedgerEntry,
)
from api.src.services.ledger import compute_held, append_audit_log, InvariantViolationError, utcnow
from api.src.services.payment.factory import get_payment_provider


async def execute_release_payout(
    session: AsyncSession,
    audit_id: uuid.UUID,
) -> Release:
    """
    Executes payout release to the verified institutional payee (F7).
    Enforces Invariants:
    1. held = donations - releases - refunds >= 0
    2. release_amount <= min(invoice_total, held)
    3. Idempotent on sender_batch_id = release_id (enforced by UNIQUE constraint)
    4. State mutation and audit log written in the same database transaction.
    """
    stmt_audit = select(Audit).where(Audit.id == audit_id)
    audit = (await session.execute(stmt_audit)).scalar_one_or_none()
    if not audit:
        raise ValueError(f"Audit {audit_id} not found.")

    if audit.decision != "RELEASE":
        raise InvariantViolationError(
            f"Cannot release funds: Audit decision is {audit.decision}, must be RELEASE."
        )

    stmt_ev = select(Evidence).where(Evidence.id == audit.evidence_id)
    evidence = (await session.execute(stmt_ev)).scalar_one()

    # Lock campaign row to serialize concurrent money operations
    stmt_camp = select(Campaign).where(Campaign.id == evidence.campaign_id).with_for_update()
    campaign = (await session.execute(stmt_camp)).scalar_one()

    stmt_payee = select(Payee).where(Payee.id == campaign.payee_id)
    payee = (await session.execute(stmt_payee)).scalar_one()

    if payee.status != "VERIFIED":
        raise InvariantViolationError(
            f"Invariant F1 Violated: Payee {payee.legal_name} status is {payee.status}, must be VERIFIED."
        )

    # Check if a release for this audit already exists (idempotency check)
    stmt_rel = select(Release).where(Release.audit_id == audit.id)
    existing_release = (await session.execute(stmt_rel)).scalar_one_or_none()
    if existing_release:
        return existing_release

    # Compute held funds
    held = await compute_held(session, campaign.id)
    invoice_total = float(evidence.extracted_json.get("total", evidence.requested_amount))
    release_amount = round(min(invoice_total, evidence.requested_amount, held), 2)

    if release_amount <= 0:
        raise InvariantViolationError(
            f"Invariant Violated: Release amount must be > 0. (Held: ${held:,.2f}, Invoice: ${invoice_total:,.2f})"
        )

    if release_amount > held:
        raise InvariantViolationError(
            f"Invariant 2 Violated: Release amount (${release_amount:,.2f}) exceeds held balance (${held:,.2f})."
        )

    release_id = f"rel_{audit.id.hex[:16]}"
    provider = get_payment_provider()

    # Execute external payout with sender_batch_id = release_id
    payout_result = await provider.create_payout(
        release_id=release_id,
        receiver_email=payee.paypal_email,
        amount=release_amount,
        currency=campaign.currency,
        note=f"Verified release for Campaign: {campaign.title}",
    )

    release = Release(
        release_id=release_id,
        campaign_id=campaign.id,
        payee_id=payee.id,
        audit_id=audit.id,
        amount=release_amount,
        paypal_batch_id=payout_result.payout_batch_id,
    )
    session.add(release)

    # Record RELEASE in ledger
    ledger_entry = LedgerEntry(
        campaign_id=campaign.id,
        type="RELEASE",
        amount=release_amount,
        paypal_ref=payout_result.payout_batch_id,
        audit_id=audit.id,
        status="CONFIRMED",
    )
    session.add(ledger_entry)

    # Append to hash-chained audit log
    await append_audit_log(
        session=session,
        event_type="FUNDS_RELEASED_TO_PAYEE",
        payload={
            "release_id": release_id,
            "campaign_id": str(campaign.id),
            "payee_id": str(payee.id),
            "payee_name": payee.legal_name,
            "payee_email": payee.paypal_email,
            "amount": release_amount,
            "paypal_batch_id": payout_result.payout_batch_id,
            "remaining_held": round(held - release_amount, 2),
        },
    )

    await session.commit()
    await session.refresh(release)
    return release
