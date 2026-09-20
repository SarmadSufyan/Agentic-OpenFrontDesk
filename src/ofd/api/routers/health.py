"""Health endpoints: liveness (`/health`) and readiness (`/health?deep=1`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ofd import __version__
from ofd.core import metrics
from ofd.core.config import settings
from ofd.db.session import ping_db
from ofd.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4")


async def _ping_redis() -> bool:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health(deep: bool = Query(False, description="Also check DB + Redis")) -> HealthResponse:
    checks: dict[str, str] = {}
    status = "ok"
    if deep:
        db_ok = await ping_db()
        redis_ok = await _ping_redis()
        checks = {
            "database": "ok" if db_ok else "down",
            "redis": "ok" if redis_ok else "down",
        }
        if not (db_ok and redis_ok):
            status = "degraded"
    return HealthResponse(status=status, version=__version__, env=settings.ENV, checks=checks)
