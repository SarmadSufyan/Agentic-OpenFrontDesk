"""Voice access endpoints: claim a concurrency-limited live-voice slot (with waitlist), and mint the
LiveKit token when granted. The browser test console / dashboard uses these instead of hitting the raw
token endpoint, so free-tier concurrency is enforced. See services/access.py.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import get_db, get_voice_identity
from ofd.core.config import settings
from ofd.core.exceptions import ConfigError, ProviderError
from ofd.services import access as access_svc
from ofd.services import tenants as tenants_svc

router = APIRouter(prefix="/voice", tags=["voice"])


class AcquireResponse(BaseModel):
    status: str  # "granted" | "queued"
    capacity: int | None = None
    # granted:
    session_ttl: int | None = None
    url: str | None = None
    token: str | None = None
    room: str | None = None
    identity: str | None = None
    # queued:
    position: int | None = None
    active: int | None = None


def _mint_token(*, tenant_id: uuid.UUID, agent_id: uuid.UUID | None) -> dict:
    try:
        from livekit import api
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("livekit-api not installed") from exc
    ident = f"caller-{uuid.uuid4().hex[:8]}"
    room = f"ofd-{tenant_id}-{uuid.uuid4().hex[:6]}"
    metadata = json.dumps(
        {"tenant_id": str(tenant_id), "agent_id": str(agent_id) if agent_id else None}
    )
    grants = api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True)
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(ident)
        .with_name(ident)
        .with_grants(grants)
        .with_metadata(metadata)
        .to_jwt()
    )
    return {"url": settings.LIVEKIT_URL, "token": token, "room": room, "identity": ident}


@router.post("/acquire", response_model=AcquireResponse)
async def acquire(
    identity: tuple = Depends(get_voice_identity),
    db: AsyncSession = Depends(get_db),
) -> AcquireResponse:
    tenant_id, email = identity
    if not (settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET):
        raise ConfigError("LiveKit is not configured (set LIVEKIT_URL / API_KEY / API_SECRET).")

    res = await access_svc.acquire(db, tenant_key=str(tenant_id), email=email)
    if res["status"] != "granted":
        return AcquireResponse(
            status="queued",
            position=res["position"],
            active=res["active"],
            capacity=res["capacity"],
        )

    _, agent = await tenants_svc.get_context(db, tenant_id=tenant_id, agent_id=None)
    lk = _mint_token(tenant_id=tenant_id, agent_id=agent.id if agent else None)
    return AcquireResponse(
        status="granted", capacity=res["capacity"], session_ttl=res["session_ttl"], **lk
    )


@router.post("/heartbeat")
async def heartbeat(identity: tuple = Depends(get_voice_identity)) -> dict:
    tenant_id, _ = identity
    return {"ok": await access_svc.heartbeat(str(tenant_id))}


@router.post("/release")
async def release(identity: tuple = Depends(get_voice_identity)) -> dict:
    tenant_id, _ = identity
    await access_svc.release(str(tenant_id))
    return {"released": True}


@router.get("/status")
async def status(identity: tuple = Depends(get_voice_identity)) -> dict:
    tenant_id, _ = identity
    return await access_svc.status(str(tenant_id))
