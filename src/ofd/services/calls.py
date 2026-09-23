"""Call persistence + read helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.call import Call, CallEvent
from ofd.models.enums import CallDirection, CallStatus
from ofd.services import webhooks


async def start_call(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
    direction: str = CallDirection.INBOUND,
    caller_number: str | None = None,
    callee_number: str | None = None,
) -> Call:
    call = Call(
        tenant_id=tenant_id,
        agent_id=agent_id,
        direction=direction,
        status=CallStatus.ACTIVE,
        caller_number=caller_number,
        callee_number=callee_number,
        started_at=datetime.now(UTC),
        transcript=[],
    )
    db.add(call)
    await db.flush()
    return call


async def finalize_call(
    db: AsyncSession,
    *,
    call_id: uuid.UUID,
    outcome: str | None = None,
    transcript: list | None = None,
    summary: str | None = None,
    latency_ms: dict | None = None,
    cost_cents: int = 0,
) -> None:
    call = await db.get(Call, call_id)
    if not call:
        return
    call.status = CallStatus.COMPLETED
    call.ended_at = datetime.now(UTC)
    if call.started_at:
        call.duration_seconds = max(0, int((call.ended_at - call.started_at).total_seconds()))
    if outcome:
        call.outcome = outcome
    if transcript is not None:
        call.transcript = transcript
    if summary:
        call.summary = summary
    if latency_ms:
        call.latency_ms = latency_ms
    call.cost_cents = cost_cents
    await db.flush()
    webhooks.emit_on_commit(
        db,
        call.tenant_id,
        "call.completed",
        {
            "id": str(call.id),
            "agent_id": str(call.agent_id) if call.agent_id else None,
            "direction": call.direction,
            "outcome": call.outcome,
            "caller_number": call.caller_number,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": call.duration_seconds,
            "summary": call.summary,
            "transcript": call.transcript or [],
        },
    )


async def add_event(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    call_id: uuid.UUID,
    seq: int,
    type: str,
    content: dict,
) -> None:
    db.add(CallEvent(tenant_id=tenant_id, call_id=call_id, seq=seq, type=type, content=content))
    await db.flush()


async def list_calls(db: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 50) -> list[Call]:
    stmt = (
        select(Call)
        .where(Call.tenant_id == tenant_id)
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_call(db: AsyncSession, *, tenant_id: uuid.UUID, call_id: uuid.UUID) -> Call | None:
    call = await db.get(Call, call_id)
    if not call or call.tenant_id != tenant_id:
        return None
    return call
