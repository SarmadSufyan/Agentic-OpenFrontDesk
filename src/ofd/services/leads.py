"""Lead / message capture."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.lead import Lead
from ofd.services import webhooks


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
    webhooks.emit_on_commit(db, tenant_id, "lead.created", lead_payload(lead))
    return lead


def lead_payload(lead: Lead) -> dict:
    return {
        "id": str(lead.id),
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "intent": lead.intent,
        "message": lead.message,
        "tags": lead.tags or [],
        "call_id": str(lead.call_id) if lead.call_id else None,
    }


async def list_leads(db: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 100) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
