"""Audit log service — record and list config-changing actions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.models.audit import AuditLog


async def record(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    target: str | None = None,
    meta: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            target=target,
            meta=meta or {},
        )
    )
    await db.flush()


async def list_audit(db: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
