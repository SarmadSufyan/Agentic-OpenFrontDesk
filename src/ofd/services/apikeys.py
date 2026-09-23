"""Tenant API keys for the public /v1 API (n8n, Zapier, Make, scripts).

Keys look like `ofd_live_<random>`. Only a SHA-256 hash is stored, so a leaked database does not
leak usable keys; the plaintext is returned once at creation. The short prefix is kept so users can
tell keys apart in the dashboard.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.exceptions import NotFound, ValidationError
from ofd.models.automation import ApiKey

KEY_PREFIX = "ofd_live_"
MAX_KEYS_PER_TENANT = 20
_TOUCH_EVERY = timedelta(minutes=1)  # throttle last_used_at writes


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


async def create_key(
    db: AsyncSession, *, tenant_id: uuid.UUID, name: str, created_by: uuid.UUID | None = None
) -> tuple[ApiKey, str]:
    name = (name or "").strip()
    if not name:
        raise ValidationError("API key name is required")
    active = await list_keys(db, tenant_id=tenant_id)
    if len([k for k in active if k.revoked_at is None]) >= MAX_KEYS_PER_TENANT:
        raise ValidationError(f"A workspace can have at most {MAX_KEYS_PER_TENANT} active keys")
    raw = generate_key()
    key = ApiKey(
        tenant_id=tenant_id,
        name=name[:120],
        prefix=raw[: len(KEY_PREFIX) + 4],
        key_hash=hash_key(raw),
        created_by=created_by,
    )
    db.add(key)
    await db.flush()
    return key, raw


async def list_keys(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def revoke_key(db: AsyncSession, *, tenant_id: uuid.UUID, key_id: uuid.UUID) -> ApiKey:
    key = await db.get(ApiKey, key_id)
    if not key or key.tenant_id != tenant_id:
        raise NotFound("API key not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        await db.flush()
    return key


async def resolve_key(db: AsyncSession, raw: str) -> ApiKey | None:
    """Return the active key matching `raw`, or None. Records last use (throttled)."""
    if not raw or not raw.startswith(KEY_PREFIX):
        return None
    stmt = select(ApiKey).where(ApiKey.key_hash == hash_key(raw))
    key = (await db.execute(stmt)).scalar_one_or_none()
    if key is None or key.revoked_at is not None:
        return None
    now = datetime.now(UTC)
    if key.last_used_at is None or now - key.last_used_at > _TOUCH_EVERY:
        key.last_used_at = now
        await db.flush()
    return key
