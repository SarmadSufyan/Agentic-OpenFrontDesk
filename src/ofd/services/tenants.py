"""Tenant / agent lookup used by the API and the agent worker."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.agent import Agent
from ofd.models.tenant import Tenant

DEMO_SLUG = "demo"


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    return (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await db.get(Tenant, tenant_id)


async def get_default_agent(db: AsyncSession, tenant_id: uuid.UUID) -> Agent | None:
    stmt = (
        select(Agent)
        .where(Agent.tenant_id == tenant_id, Agent.is_active.is_(True))
        .order_by(Agent.created_at)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_context(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
) -> tuple[Tenant | None, Agent | None]:
    """Resolve (tenant, agent). Falls back to the demo tenant when nothing is specified."""
    tenant = None
    if tenant_id:
        tenant = await get_tenant(db, tenant_id)
    if tenant is None:
        tenant = await get_tenant_by_slug(db, DEMO_SLUG)
    if tenant is None:
        return None, None

    agent = None
    if agent_id:
        agent = await db.get(Agent, agent_id)
    if agent is None or agent.tenant_id != tenant.id:
        agent = await get_default_agent(db, tenant.id)
    return tenant, agent


_TENANT_FIELDS = {"name", "vertical", "timezone", "business_hours", "address", "settings"}
_AGENT_FIELDS = {
    "name",
    "voice",
    "greeting",
    "tone",
    "persona",
    "escalation_rules",
    "booking_rules",
    "is_active",
}


async def update_tenant(db: AsyncSession, tenant: Tenant, data: dict) -> Tenant:
    for k, v in data.items():
        if k in _TENANT_FIELDS and v is not None:
            if k == "settings":  # merge, so a partial update never wipes other keys
                v = {**(tenant.settings or {}), **v}
            setattr(tenant, k, v)
    await db.flush()
    return tenant


async def update_agent(db: AsyncSession, agent: Agent, data: dict) -> Agent:
    for k, v in data.items():
        if k in _AGENT_FIELDS and v is not None:
            setattr(agent, k, v)
    await db.flush()
    return agent
