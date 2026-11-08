import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models import LedgerEntry, AuditLog, Campaign


def utcnow():
    return datetime.now(timezone.utc)



class InvariantViolationError(Exception):
    """Raised when a core money invariant or rule is violated."""
    pass


GENESIS_HASH = "0" * 64


def canonical_json_dumps(payload: Dict[str, Any]) -> str:
    """Formats JSON canonically (keys sorted, no extra whitespace) for reproducible hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


async def compute_held(session: AsyncSession, campaign_id: uuid.UUID) -> float:
    """
    Computes available held balance for a campaign:
    held = sum(DONATION) - sum(RELEASE) - sum(REFUND)
    Invariant 1: held balance can never be negative.
    """
    stmt = (
        select(LedgerEntry.type, func.coalesce(func.sum(LedgerEntry.amount), 0.0))
        .where(LedgerEntry.campaign_id == campaign_id)
        .where(LedgerEntry.status == "CONFIRMED")
        .group_by(LedgerEntry.type)
    )
    result = await session.execute(stmt)
    totals = {row[0]: float(row[1]) for row in result.all()}

    donations = totals.get("DONATION", 0.0)
    releases = totals.get("RELEASE", 0.0)
    refunds = totals.get("REFUND", 0.0)

    held = round(donations - releases - refunds, 2)
    if held < -0.001:  # Floating point tolerance
        raise InvariantViolationError(
            f"Invariant 1 Violated: Negative held balance for campaign {campaign_id}! (Held: {held})"
        )
    return max(held, 0.0)


async def get_campaign_financials(session: AsyncSession, campaign_id: uuid.UUID) -> Dict[str, float]:
    """Returns total donations, releases, refunds, and available held balance."""
    stmt = (
        select(LedgerEntry.type, func.coalesce(func.sum(LedgerEntry.amount), 0.0))
        .where(LedgerEntry.campaign_id == campaign_id)
        .where(LedgerEntry.status == "CONFIRMED")
        .group_by(LedgerEntry.type)
    )
    result = await session.execute(stmt)
    totals = {row[0]: float(row[1]) for row in result.all()}

    donations = totals.get("DONATION", 0.0)
    releases = totals.get("RELEASE", 0.0)
    refunds = totals.get("REFUND", 0.0)
    held = max(round(donations - releases - refunds, 2), 0.0)

    return {
        "total_donations": donations,
        "total_releases": releases,
        "total_refunds": refunds,
        "held_balance": held,
    }


async def append_audit_log(
    session: AsyncSession,
    event_type: str,
    payload: Dict[str, Any],
) -> AuditLog:
    """
    Appends a new event to the tamper-evident SHA-256 hash chain.
    Takes pg_advisory_xact_lock(1) to strictly prevent concurrent transaction chain forks.
    """
    # Advisory lock for concurrency protection (supported in PostgreSQL)
    try:
        await session.execute(text("SELECT pg_advisory_xact_lock(1);"))
    except Exception:
        # Fallback for environments without Postgres advisory lock
        pass

    # Find the most recent block in the chain
    stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    last_entry = (await session.execute(stmt)).scalar_one_or_none()

    prev_hash = last_entry.hash if last_entry else GENESIS_HASH
    canonical_body = canonical_json_dumps(payload)
    
    # Compute block hash: SHA-256(prev_hash:event_type:canonical_json)
    hasher = hashlib.sha256()
    hasher.update(f"{prev_hash}:{event_type}:{canonical_body}".encode("utf-8"))
    block_hash = hasher.hexdigest()

    log_entry = AuditLog(
        prev_hash=prev_hash,
        hash=block_hash,
        event_type=event_type,
        payload_json=payload,
    )
    session.add(log_entry)
    await session.flush()
    return log_entry


async def verify_audit_chain(session: AsyncSession) -> Dict[str, Any]:
    """
    Verifies cryptographic hash-chain integrity from genesis to head.
    Returns valid=True or failure details.
    """
    stmt = select(AuditLog).order_by(AuditLog.seq.asc())
    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return {"valid": True, "total_entries": 0, "head_hash": GENESIS_HASH, "error": None}

    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            return {
                "valid": False,
                "total_entries": len(entries),
                "error": f"Chain broken at seq {entry.seq}: expected prev_hash {expected_prev}, got {entry.prev_hash}",
            }

        canonical_body = canonical_json_dumps(entry.payload_json)
        hasher = hashlib.sha256()
        hasher.update(f"{entry.prev_hash}:{entry.event_type}:{canonical_body}".encode("utf-8"))
        computed_hash = hasher.hexdigest()

        if computed_hash != entry.hash:
            return {
                "valid": False,
                "total_entries": len(entries),
                "error": f"Tampering detected at seq {entry.seq}: computed hash {computed_hash} != stored hash {entry.hash}",
            }

        expected_prev = entry.hash

    return {
        "valid": True,
        "total_entries": len(entries),
        "head_hash": entries[-1].hash,
        "error": None,
    }
