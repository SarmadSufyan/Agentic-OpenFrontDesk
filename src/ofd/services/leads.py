"""Lead / message capture."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.lead import Lead


async def capture_lead(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    intent: str | None = None,
    message: str | None = None,
    call_id: uuid.UUID | None = None,
    tags: list[str] | None = None,
) -> Lead:
    lead = Lead(
        tenant_id=tenant_id,
        call_id=call_id,
        name=name,
        phone=phone,
        email=email,
        intent=intent,
        message=message,
        tags=tags or [],
    )
    db.add(lead)
    await db.flush()
    return lead


async def list_leads(db: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 100) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
