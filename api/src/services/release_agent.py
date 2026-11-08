import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models import (
    Campaign,
    Evidence,
    Audit,
    AgentTrace,
)
from api.src.services.ledger import compute_held, append_audit_log, utcnow
from api.src.services.release import execute_release_payout


async def log_agent_trace(
    session: AsyncSession,
    audit_id: uuid.UUID,
    step: int,
    tool: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
) -> AgentTrace:
    """Records an autonomous execution step in the agent_traces table."""
    trace = AgentTrace(
        audit_id=audit_id,
        step=step,
        tool=tool,
        input_json=input_data,
        output_json=output_data,
    )
    session.add(trace)
    await session.flush()
    return trace


async def run_case(
    session: AsyncSession,
    audit_id: uuid.UUID,
) -> List[Dict[str, Any]]:
    """
    Minimal Release Agent execution pipeline (F11).
    Works one case end-to-end through a transparent, logged sequence of steps:
    1. get_ledger: Check available held funds.
    2. run_checks: Evaluate deterministic hard checks and soft signals.
    3. decide: Calculate risk score and select decision.
    4. act: Execute payout release (only if checks pass) or route to human review.
    5. explain: Formulate plain-language rationale.
    """
    stmt = select(Audit).where(Audit.id == audit_id)
    audit = (await session.execute(stmt)).scalar_one_or_none()
    if not audit:
        raise ValueError(f"Audit {audit_id} not found.")

    stmt_ev = select(Evidence).where(Evidence.id == audit.evidence_id)
    evidence = (await session.execute(stmt_ev)).scalar_one()

    stmt_camp = select(Campaign).where(Campaign.id == evidence.campaign_id)
    campaign = (await session.execute(stmt_camp)).scalar_one()

    traces = []

    # STEP 1: get_ledger
    held_balance = await compute_held(session, campaign.id)
    t1 = await log_agent_trace(
        session=session,
        audit_id=audit.id,
        step=1,
        tool="get_ledger",
        input_data={"campaign_id": str(campaign.id)},
        output_data={"held_balance": held_balance, "currency": campaign.currency},
    )
    traces.append({"step": 1, "tool": "get_ledger", "output": t1.output_json})

    # STEP 2: run_checks
    hard_checks = audit.checks_json.get("hard_checks", {})
    soft_signals = audit.checks_json.get("soft_signals", {})
    all_hard_passed = all(hc.get("passed", False) for hc in hard_checks.values())
    t2 = await log_agent_trace(
        session=session,
        audit_id=audit.id,
        step=2,
        tool="run_checks",
        input_data={"evidence_id": str(evidence.id)},
        output_data={
            "all_hard_passed": all_hard_passed,
            "hard_checks_evaluated": list(hard_checks.keys()),
            "soft_signals_evaluated": list(soft_signals.keys()),
        },
    )
    traces.append({"step": 2, "tool": "run_checks", "output": t2.output_json})

    # STEP 3: decide
    t3 = await log_agent_trace(
        session=session,
        audit_id=audit.id,
        step=3,
        tool="decide",
        input_data={"risk_score": audit.risk_score, "all_hard_passed": all_hard_passed},
        output_data={"decision": audit.decision, "risk_score": audit.risk_score},
    )
    traces.append({"step": 3, "tool": "decide", "output": t3.output_json})

    # STEP 4: act
    act_output = {}
    if audit.decision == "RELEASE":
        try:
            rel = await execute_release_payout(session, audit.id)
            act_output = {
                "action": "RELEASE_EXECUTED",
                "release_id": rel.release_id,
                "amount": rel.amount,
                "paypal_batch_id": rel.paypal_batch_id,
            }
        except Exception as exc:
            act_output = {"action": "RELEASE_FAILED", "error": str(exc)}
    else:
        act_output = {
            "action": "ESCALATED_TO_REVIEWER_QUEUE",
            "reason": audit.explanation,
        }

    t4 = await log_agent_trace(
        session=session,
        audit_id=audit.id,
        step=4,
        tool="release_funds" if audit.decision == "RELEASE" else "escalate",
        input_data={"decision": audit.decision},
        output_data=act_output,
    )
    traces.append({"step": 4, "tool": t4.tool, "output": t4.output_json})

    # STEP 5: explain
    t5 = await log_agent_trace(
        session=session,
        audit_id=audit.id,
        step=5,
        tool="explain_decision",
        input_data={"decision": audit.decision, "risk_score": audit.risk_score},
        output_data={"rationale": audit.explanation},
    )
    traces.append({"step": 5, "tool": "explain_decision", "output": t5.output_json})

    await session.commit()
    return traces

