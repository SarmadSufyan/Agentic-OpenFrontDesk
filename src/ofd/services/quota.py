"""Per-tenant rate limiting / quotas backed by Redis (fixed-window counters).

Protects the free provider tiers and controls spend. Used by the API via the `rate_limit` dependency
and can be called by the worker before starting a call. See docs/13-security-compliance.md.
"""

from __future__ import annotations

import time
import uuid

from ofd.core.config import settings


async def check_rate(
    tenant_id: uuid.UUID,
    resource: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """Increment the tenant's counter for `resource` in the current window.

    Returns (allowed, remaining). Fails open (allowed) if Redis is unreachable — availability over
    strictness for a rate limiter.
    """
    return await hit(f"{tenant_id}:{resource}", limit, window_seconds)


async def hit(subject: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
    """Fixed-window counter for any subject (a tenant resource, a hashed client IP, ...)."""
    import redis.asyncio as aioredis

    bucket = int(time.time() // window_seconds)
    key = f"rl:{subject}:{bucket}"
    client = aioredis.from_url(settings.REDIS_URL)
    try:
        count = int(await client.incr(key))
        if count == 1:
            await client.expire(key, window_seconds)
    except Exception:
        return True, limit  # fail open
    finally:
        try:
            await client.aclose()
        except Exception:
            pass
    return count <= limit, max(0, limit - count)
