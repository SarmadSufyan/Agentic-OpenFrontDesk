"""Access engine for live voice sessions: concurrency cap + FIFO waitlist + priority allowlist.

The expensive resource (a live voice session) is capped by MAX_CONCURRENT_VOICE. Extra users wait in
a FIFO queue and are admitted as slots free up. Allowlisted emails skip the queue. Active slots live in
Redis with a TTL (score = expiry) so a crashed/closed client frees its slot automatically.

Cheap features (accounts, knowledge, text chat, the widget) are NOT gated by this.
"""

from __future__ import annotations

import time

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.models.access import AllowlistEntry

_ACTIVE = "voice:active"
_QUEUE = "voice:queue"


def _client():
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def is_allowlisted(db: AsyncSession, email: str | None) -> bool:
    if not email:
        return False
    email = email.lower()
    if email in settings.access_allowlist:
        return True
    row = (await db.execute(select(AllowlistEntry.id).where(AllowlistEntry.email == email))).first()
    return row is not None


async def acquire(db: AsyncSession, *, tenant_key: str, email: str | None) -> dict:
    """Try to claim a voice slot. Returns {status: 'granted'|'queued', ...}."""
    cap = settings.MAX_CONCURRENT_VOICE
    ttl = settings.VOICE_SESSION_TTL_SECONDS
    now = int(time.time())
    allow = await is_allowlisted(db, email)
    r = _client()
    try:
        await r.zremrangebyscore(_ACTIVE, "-inf", now)  # drop expired slots

        # already holding a slot? refresh it.
        if await r.zscore(_ACTIVE, tenant_key) is not None:
            await r.zadd(_ACTIVE, {tenant_key: now + ttl})
            await r.zrem(_QUEUE, tenant_key)
            return _granted(cap)

        if allow:
            await r.zadd(_ACTIVE, {tenant_key: now + ttl})
            await r.zrem(_QUEUE, tenant_key)
            return _granted(cap, allowlisted=True)

        active = await r.zcard(_ACTIVE)
        await r.zadd(_QUEUE, {tenant_key: now}, nx=True)  # ensure queued (keeps original position)
        rank = await r.zrank(_QUEUE, tenant_key)
        rank = 0 if rank is None else rank
        free = cap - active
        if rank < free:
            await r.zrem(_QUEUE, tenant_key)
            await r.zadd(_ACTIVE, {tenant_key: now + ttl})
            return _granted(cap)
        return {
            "status": "queued",
            "position": rank + 1,
            "active": active,
            "capacity": cap,
        }
    finally:
        await r.aclose()


def _granted(cap: int, *, allowlisted: bool = False) -> dict:
    return {
        "status": "granted",
        "session_ttl": settings.VOICE_SESSION_TTL_SECONDS,
        "capacity": cap,
        "allowlisted": allowlisted,
    }


async def heartbeat(tenant_key: str) -> bool:
    """Refresh a held slot's TTL. Returns False if the slot expired (client must re-acquire)."""
    now = int(time.time())
    r = _client()
    try:
        await r.zremrangebyscore(_ACTIVE, "-inf", now)
        updated = await r.zadd(
            _ACTIVE, {tenant_key: now + settings.VOICE_SESSION_TTL_SECONDS}, xx=True
        )
        return bool(updated) or (await r.zscore(_ACTIVE, tenant_key)) is not None
    finally:
        await r.aclose()


async def release(tenant_key: str) -> None:
    r = _client()
    try:
        await r.zrem(_ACTIVE, tenant_key)
        await r.zrem(_QUEUE, tenant_key)
    finally:
        await r.aclose()


async def status(tenant_key: str) -> dict:
    now = int(time.time())
    r = _client()
    try:
        await r.zremrangebyscore(_ACTIVE, "-inf", now)
        active = await r.zcard(_ACTIVE)
        is_active = (await r.zscore(_ACTIVE, tenant_key)) is not None
        rank = await r.zrank(_QUEUE, tenant_key)
        return {
            "capacity": settings.MAX_CONCURRENT_VOICE,
            "active": active,
            "holding_slot": is_active,
            "queue_position": (rank + 1) if rank is not None else None,
            "queue_length": await r.zcard(_QUEUE),
        }
    finally:
        await r.aclose()


# --- admin views + allowlist management ---
async def admin_snapshot() -> dict:
    now = int(time.time())
    r = _client()
    try:
        await r.zremrangebyscore(_ACTIVE, "-inf", now)
        active = await r.zrange(_ACTIVE, 0, -1, withscores=True)
        queue = await r.zrange(_QUEUE, 0, -1)
        return {
            "capacity": settings.MAX_CONCURRENT_VOICE,
            "active": [{"tenant": m, "expires_in": int(s) - now} for m, s in active],
            "queue": list(queue),
        }
    finally:
        await r.aclose()


async def add_allowlist(db: AsyncSession, *, email: str, note: str | None = None) -> AllowlistEntry:
    email = email.strip().lower()
    existing = (
        await db.execute(select(AllowlistEntry).where(AllowlistEntry.email == email))
    ).scalar_one_or_none()
    if existing:
        if note:
            existing.note = note
        await db.flush()
        return existing
    entry = AllowlistEntry(email=email, note=note)
    db.add(entry)
    await db.flush()
    return entry


async def remove_allowlist(db: AsyncSession, *, email: str) -> None:
    await db.execute(sa_delete(AllowlistEntry).where(AllowlistEntry.email == email.strip().lower()))
    await db.flush()


async def list_allowlist(db: AsyncSession) -> list[AllowlistEntry]:
    return list(
        (await db.execute(select(AllowlistEntry).order_by(AllowlistEntry.created_at.desc())))
        .scalars()
        .all()
    )
