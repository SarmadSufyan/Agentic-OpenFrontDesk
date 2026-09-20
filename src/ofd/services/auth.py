"""Auth service: signup (user + first tenant + owner membership + default agent) and login."""

from __future__ import annotations

import re
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.exceptions import Conflict, Unauthorized, ValidationError
from ofd.core.security import hash_password, verify_password
from ofd.models.agent import Agent
from ofd.models.enums import Role
from ofd.models.tenant import Membership, Tenant
from ofd.models.user import User

DEFAULT_HOURS = {d: ["09:00", "17:00"] for d in ["mon", "tue", "wed", "thu", "fri"]}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "workspace"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    base = _slugify(base)
    slug = base
    while (await db.execute(select(Tenant.id).where(Tenant.slug == slug))).first() is not None:
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


async def signup(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    name: str | None = None,
    business_name: str | None = None,
) -> tuple[User, Tenant]:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValidationError("A valid email is required")
    if len(password or "") < 8:
        raise ValidationError("Password must be at least 8 characters")

    exists = (await db.execute(select(User.id).where(User.email == email))).first()
    if exists is not None:
        raise Conflict("An account with that email already exists")

    user = User(email=email, password_hash=hash_password(password), name=name)
    db.add(user)
    await db.flush()

    biz = business_name or (name or email.split("@")[0])
    tenant = Tenant(
        name=biz,
        slug=await _unique_slug(db, biz),
        timezone="UTC",
        business_hours=DEFAULT_HOURS,
        address={},
        settings={},
        plan="free",
    )
    db.add(tenant)
    await db.flush()

    db.add(Membership(tenant_id=tenant.id, user_id=user.id, role=Role.OWNER))
    db.add(
        Agent(
            tenant_id=tenant.id,
            name="Front Desk",
            greeting=f"Thanks for calling {biz}! How can I help you today?",
            booking_rules={"slot_minutes": 30, "services": []},
        )
    )
    await db.flush()
    return user, tenant


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    email = (email or "").strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password")
    if not user.is_active:
        raise Unauthorized("Account is disabled")
    return user


async def list_memberships(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Membership, Tenant]]:
    stmt = (
        select(Membership, Tenant)
        .join(Tenant, Tenant.id == Membership.tenant_id)
        .where(Membership.user_id == user_id)
        .order_by(Membership.created_at)
    )
    return [(m, t) for m, t in (await db.execute(stmt)).all()]


async def first_tenant_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID | None:
    row = (
        await db.execute(
            select(Membership.tenant_id)
            .where(Membership.user_id == user_id)
            .order_by(Membership.created_at)
            .limit(1)
        )
    ).first()
    return row[0] if row else None


async def role_in_tenant(
    db: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> str | None:
    row = (
        await db.execute(
            select(Membership.role).where(
                Membership.user_id == user_id, Membership.tenant_id == tenant_id
            )
        )
    ).first()
    return row[0] if row else None
