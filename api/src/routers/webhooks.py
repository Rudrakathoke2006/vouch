import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.database import get_db
from api.src.models import WebhookEvent, AgentTrace
from api.src.services.payment.factory import get_payment_provider
from api.src.services.sweeper import run_deadline_sweeper
from api.src.services.reconcile import run_ledger_reconcile
from api.src.services.release_agent import run_case
from api.src.services.ledger import append_audit_log


router = APIRouter(tags=["Webhooks & Admin"])


@router.post("/webhooks/paypal")
async def handle_paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    PayPal Webhook Receiver (Fix 2).
    Verifies cryptographic PayPal transmission headers via /v1/notifications/verify-webhook-signature.
    Enforces deduplication on paypal_event_id.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    provider = get_payment_provider()
    verify_result = await provider.verify_webhook(headers=headers, raw_body=raw_body)

    if not verify_result.verified:
        raise HTTPException(
            status_code=400,
            detail=f"PayPal webhook verification failed: {verify_result.status}",
        )

    event_id = verify_result.event_id or f"evt_{uuid.uuid4().hex[:12]}"
    event_type = verify_result.event_type or "UNKNOWN_EVENT"

    # Idempotently check if event was already recorded (replay protection)
    stmt = select(WebhookEvent).where(WebhookEvent.paypal_event_id == event_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return {"status": "already_processed", "event_id": event_id}

    webhook_record = WebhookEvent(
        paypal_event_id=event_id,
        event_type=event_type,
        payload_json=verify_result.resource,
        status="PROCESSED",
    )
    db.add(webhook_record)

    await append_audit_log(
        session=db,
        event_type=f"WEBHOOK_{event_type.replace('.', '_').upper()}",
        payload={
            "event_id": event_id,
            "event_type": event_type,
            "resource": verify_result.resource,
        },
    )

    await db.commit()
    return {"status": "accepted", "event_id": event_id}


@router.post("/admin/tick")
async def trigger_deadline_sweeper(db: AsyncSession = Depends(get_db)):
    """
    Deadline Clock and Sweeper (F8).
    Finds expired campaigns and issues pro-rata refunds for unreleased funds.
    """
    summary = await run_deadline_sweeper(db)
    return summary


@router.post("/admin/reconcile")
async def trigger_ledger_reconcile(db: AsyncSession = Depends(get_db)):
    """
    Reconciles pending SUBMITTED ledger entries with PayPal API status (Fix 2).
    """
    summary = await run_ledger_reconcile(db)
    return summary


@router.get("/audits/{audit_id}/trace")
async def get_audit_trace(audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves the autonomous step trace of the Release Agent (F11)."""
    stmt = select(AgentTrace).where(AgentTrace.audit_id == audit_id).order_by(AgentTrace.step.asc())
    traces = (await db.execute(stmt)).scalars().all()
    return traces


@router.post("/audits/{audit_id}/run-agent")
async def execute_agent_case(audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Executes the Release Agent pipeline for an audited case (F11)."""
    traces = await run_case(session=db, audit_id=audit_id)
    return {"audit_id": str(audit_id), "status": "COMPLETED", "traces": traces}
