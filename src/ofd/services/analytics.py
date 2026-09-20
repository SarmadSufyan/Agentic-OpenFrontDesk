"""Analytics overview for a tenant's dashboard."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.booking import Booking
from ofd.models.call import Call
from ofd.models.lead import Lead


async def overview(db: AsyncSession, *, tenant_id: uuid.UUID) -> dict:
    calls_total = (
        await db.execute(select(func.count(Call.id)).where(Call.tenant_id == tenant_id))
    ).scalar_one()

    by_outcome_rows = (
        await db.execute(
            select(Call.outcome, func.count(Call.id))
            .where(Call.tenant_id == tenant_id)
            .group_by(Call.outcome)
        )
    ).all()
    calls_by_outcome = {(o or "unknown"): c for o, c in by_outcome_rows}

    seconds_total = (
        await db.execute(
            select(func.coalesce(func.sum(Call.duration_seconds), 0)).where(
                Call.tenant_id == tenant_id
            )
        )
    ).scalar_one()

    bookings_total = (
        await db.execute(select(func.count(Booking.id)).where(Booking.tenant_id == tenant_id))
    ).scalar_one()
    leads_total = (
        await db.execute(select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id))
    ).scalar_one()

    return {
        "calls_total": int(calls_total),
        "calls_by_outcome": calls_by_outcome,
        "bookings_total": int(bookings_total),
        "leads_total": int(leads_total),
        "minutes_total": round(int(seconds_total) / 60, 1),
        "avg_latency_ms": None,
    }
