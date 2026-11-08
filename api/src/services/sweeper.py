import uuid
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models import (
    Campaign,
    Donation,
    Refund,
    LedgerEntry,
)
from api.src.services.ledger import compute_held, append_audit_log, InvariantViolationError, utcnow
from api.src.services.payment.factory import get_payment_provider


async def run_deadline_sweeper(session: AsyncSession) -> Dict[str, Any]:
    """
    Automatic deadline clock and refund sweeper (F8).
    Finds expired campaigns, refunds all unreleased donations pro rata automatically,
    and closes the campaign.
    Enforces Invariants:
    1. held = donations - releases - refunds >= 0
    2. A donation capture is refunded at most once (UNIQUE constraint on donation_id)
    3. Idempotent external refund calls
    4. State mutation and audit log written in the same transaction.
    """
    now = utcnow()
    # Find active campaigns whose proof deadline has expired
    stmt = (
        select(Campaign)
        .where(Campaign.status == "ACTIVE")
        .where(Campaign.proof_deadline <= now)
    )
    result = await session.execute(stmt)
    expired_campaigns = result.scalars().all()

    swept_count = 0
    refunds_issued = 0
    total_refunded_amount = 0.0

    provider = get_payment_provider()

    for camp in expired_campaigns:
        # Lock campaign row
        stmt_lock = select(Campaign).where(Campaign.id == camp.id).with_for_update()
        campaign = (await session.execute(stmt_lock)).scalar_one()

        held = await compute_held(session, campaign.id)

        if held > 0:
            # Query captured donations that have not been refunded yet
            stmt_don = (
                select(Donation)
                .outerjoin(Refund, Donation.id == Refund.donation_id)
                .where(Donation.campaign_id == campaign.id)
                .where(Donation.status == "CAPTURED")
                .where(Refund.id == None)  # Not refunded
                .order_by(Donation.created_at.asc())
            )
            donations = (await session.execute(stmt_don)).scalars().all()

            if donations:
                total_donated = sum(d.amount for d in donations)
                remaining_pool = held

                for idx, don in enumerate(donations):
                    # Pro-rata refund calculation
                    if idx == len(donations) - 1:
                        # Last donation receives remaining held fraction to avoid rounding drift
                        refund_amount = min(don.amount, remaining_pool)
                    else:
                        pro_rata = (don.amount / total_donated) * held
                        refund_amount = round(min(don.amount, pro_rata), 2)

                    if refund_amount <= 0:
                        continue

                    refund_req_id = f"sweeper_ref_{don.id.hex[:12]}"
                    refund_res = await provider.refund_capture(
                        capture_id=don.paypal_capture_id,
                        amount=refund_amount,
                        request_id=refund_req_id,
                        currency=campaign.currency,
                        note="Automatic pro-rata refund: campaign proof deadline expired without spending verification.",
                    )

                    refund_entry = Refund(
                        donation_id=don.id,
                        amount=refund_amount,
                        paypal_refund_id=refund_res.refund_id,
                        reason="Proof deadline expired without spending verification",
                    )
                    session.add(refund_entry)

                    ledger_entry = LedgerEntry(
                        campaign_id=campaign.id,
                        type="REFUND",
                        amount=refund_amount,
                        paypal_ref=refund_res.refund_id,
                        status="CONFIRMED",
                    )
                    session.add(ledger_entry)

                    don.status = "REFUNDED"
                    remaining_pool = round(remaining_pool - refund_amount, 2)
                    refunds_issued += 1
                    total_refunded_amount += refund_amount

                    await append_audit_log(
                        session=session,
                        event_type="DONATION_AUTOMATICALLY_REFUNDED",
                        payload={
                            "donation_id": str(don.id),
                            "campaign_id": str(campaign.id),
                            "amount": refund_amount,
                            "paypal_refund_id": refund_res.refund_id,
                            "reason": "Deadline lapsed",
                        },
                    )

        # Close the campaign
        campaign.status = "CLOSED"
        await append_audit_log(
            session=session,
            event_type="CAMPAIGN_CLOSED_BY_SWEEPER",
            payload={
                "campaign_id": str(campaign.id),
                "title": campaign.title,
                "reason": "Proof deadline lapsed",
            },
        )

        swept_count += 1
        await session.commit()

    return {
        "swept_campaigns": swept_count,
        "refunds_issued": refunds_issued,
        "total_refunded_amount": round(total_refunded_amount, 2),
    }
