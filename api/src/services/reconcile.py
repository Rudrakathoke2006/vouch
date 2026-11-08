import uuid
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models import LedgerEntry
from api.src.services.ledger import append_audit_log, utcnow
from api.src.services.payment.factory import get_payment_provider


async def run_ledger_reconcile(session: AsyncSession) -> Dict[str, Any]:
    """
    Reconciles pending ledger entries with PayPal API status (Fix 2).
    Scans entries stuck in SUBMITTED status and cross-checks status against PayPal.
    Moves status to CONFIRMED or FAILED.
    Webhooks only confirm; the ledger never depends on them arriving.
    """
    stmt = (
        select(LedgerEntry)
        .where(LedgerEntry.status == "SUBMITTED")
        .order_by(LedgerEntry.created_at.asc())
    )
    result = await session.execute(stmt)
    pending_entries = result.scalars().all()

    provider = get_payment_provider()
    reconciled_count = 0
    mismatches = 0

    for entry in pending_entries:
        try:
            if entry.type == "DONATION":
                cap = await provider.get_capture(entry.paypal_ref)
                if cap.status in ("COMPLETED", "SUCCESS"):
                    entry.status = "CONFIRMED"
                    reconciled_count += 1
                else:
                    entry.status = "FAILED"
                    mismatches += 1

            elif entry.type == "RELEASE":
                payout = await provider.get_payout(entry.paypal_ref)
                if payout.status in ("SUCCESS", "COMPLETED"):
                    entry.status = "CONFIRMED"
                    reconciled_count += 1
                else:
                    entry.status = "FAILED"
                    mismatches += 1

            await append_audit_log(
                session=session,
                event_type="LEDGER_ENTRY_RECONCILED",
                payload={
                    "ledger_entry_id": str(entry.id),
                    "type": entry.type,
                    "paypal_ref": entry.paypal_ref,
                    "new_status": entry.status,
                },
            )
        except Exception as exc:
            mismatches += 1
            await append_audit_log(
                session=session,
                event_type="LEDGER_RECONCILE_ERROR",
                payload={
                    "ledger_entry_id": str(entry.id),
                    "error": str(exc),
                },
            )

    await session.commit()
    return {
        "reconciled_count": reconciled_count,
        "mismatches": mismatches,
    }
