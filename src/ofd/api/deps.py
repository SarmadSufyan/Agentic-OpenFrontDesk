"""FastAPI dependencies: DB session, authenticated user, tenant scoping, roles.

Two ways to resolve the tenant:
- `get_context` / `get_current_user`: require a valid Bearer access token (production path).
- `get_active_tenant_id`: token if present, else (dev only) `?tenant=<slug>` defaulting to "demo" —
  keeps the pre-auth knowledge/voice demo usable while auth exists alongside it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import Forbidden, TooManyRequests, Unauthorized
from ofd.core.security import decode_token
from ofd.db.session import get_db
from ofd.models.tenant import Tenant
from ofd.models.user import User
from ofd.services import auth as auth_svc
from ofd.services import quota as quota_svc
from ofd.services import tenants as tenants_svc

__all__ = [
    "get_db",
    "get_current_user",
    "get_context",
    "get_active_tenant_id",
    "get_voice_identity",
    "require_roles",
    "require_admin",
    "rate_limit",
    "AuthContext",
]

bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    tenant: Tenant
    role: str


async def _auth(creds: HTTPAuthorizationCredentials | None, db: AsyncSession) -> tuple[dict, User]:
    if creds is None:
        raise Unauthorized("Authentication required")
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise Unauthorized("Invalid token type")
    sub = payload.get("sub")
    user = await db.get(User, uuid.UUID(sub)) if sub else None
    if not user or not user.is_active:
        raise Unauthorized("User not found or inactive")
    return payload, user


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    _, user = await _auth(creds, db)
    return user


async def get_context(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    payload, user = await _auth(creds, db)
    tid = payload.get("tid")
    tenant = await db.get(Tenant, uuid.UUID(tid)) if tid else None
    if tenant is None:
        raise Unauthorized("No active workspace in token")
    role = await auth_svc.role_in_tenant(db, user_id=user.id, tenant_id=tenant.id)
    if role is None:
        raise Forbidden("Not a member of this workspace")
    return AuthContext(user=user, tenant=tenant, role=role)


def require_roles(*roles: str):
    async def dep(ctx: AuthContext = Depends(get_context)) -> AuthContext:
        if ctx.role not in roles:
            raise Forbidden("Insufficient permissions")
        return ctx

    return dep


async def get_active_tenant_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    tenant: str | None = Query(None, description="Dev-only tenant slug when unauthenticated"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    if creds is not None:
        payload = decode_token(creds.credentials)
        tid = payload.get("tid")
        if tid:
            return uuid.UUID(tid)
    if not settings.is_production:
        t = await tenants_svc.get_tenant_by_slug(db, tenant or "demo")
        if t:
            return t.id
    raise Unauthorized("Authentication required")


def rate_limit(resource: str, per_min: int | None = None):
    """Dependency factory: enforce a per-tenant rate limit and return the tenant_id."""

    async def dep(tenant_id: uuid.UUID = Depends(get_active_tenant_id)) -> uuid.UUID:
        if settings.RATE_LIMIT_ENABLED:
            limit = per_min or settings.RATE_LIMIT_PER_MIN
            allowed, _ = await quota_svc.check_rate(tenant_id, resource, limit, 60)
            if not allowed:
                raise TooManyRequests(f"Rate limit exceeded for {resource} ({limit}/min)")
        return tenant_id

    return dep


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Platform admin (email listed in ADMIN_EMAILS)."""
    if user.email.lower() not in settings.admin_emails:
        raise Forbidden("Admin access required")
    return user


async def get_voice_identity(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    tenant: str | None = Query(None, description="Dev-only tenant slug when unauthenticated"),
    db: AsyncSession = Depends(get_db),
) -> tuple[uuid.UUID, str | None]:
    """Resolve (tenant_id, email) for voice-access gating: from the token, else dev tenant slug."""
    if creds is not None:
        payload = decode_token(creds.credentials)
        tid = payload.get("tid")
        if tid:
            email = None
            sub = payload.get("sub")
            if sub:
                u = await db.get(User, uuid.UUID(sub))
                email = u.email if u else None
            return uuid.UUID(tid), email
    if not settings.is_production:
        t = await tenants_svc.get_tenant_by_slug(db, tenant or "demo")
        if t:
            return t.id, None
    raise Unauthorized("Authentication required")
