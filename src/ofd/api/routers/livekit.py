"""LiveKit token minting for browser test calls (free, no telephony).

The dashboard/test page calls `GET /livekit/token` to receive a short-lived token + the LiveKit URL,
then connects via WebRTC. The agent worker (ofd.agent) joins the same room. See docs/08-telephony.md.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ofd.core.config import settings
from ofd.core.exceptions import ConfigError, ProviderError
from ofd.core.logging import get_logger
from ofd.db.session import session_scope
from ofd.services import tenants as tenants_svc

logger = get_logger("ofd.api.livekit")

router = APIRouter(prefix="/livekit", tags=["livekit"])


class TokenResponse(BaseModel):
    url: str
    token: str
    room: str
    identity: str


async def _tenant_metadata(tenant_slug: str) -> str | None:
    """Best-effort JSON metadata {tenant_id, agent_id} so the agent knows which business to be."""
    try:
        async with session_scope() as db:
            tenant, agent = await tenants_svc.get_context(
                db, tenant_id=None, agent_id=None
            ) if tenant_slug == "demo" else (
                await tenants_svc.get_tenant_by_slug(db, tenant_slug),
                None,
            )
            if tenant is None:
                return None
            if agent is None:
                agent = await tenants_svc.get_default_agent(db, tenant.id)
            return json.dumps(
                {
                    "tenant_id": str(tenant.id),
                    "agent_id": str(agent.id) if agent else None,
                }
            )
    except Exception as exc:  # DB not seeded/available — issue token without metadata
        logger.warning("token_tenant_lookup_failed", error=str(exc))
        return None


@router.get("/token", response_model=TokenResponse)
async def create_token(
    room: str = Query("ofd-test", description="Room to join"),
    tenant: str = Query("demo", description="Tenant slug the agent should represent"),
    identity: str | None = Query(None, description="Caller identity (auto if omitted)"),
) -> TokenResponse:
    if not (settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET):
        raise ConfigError(
            "LiveKit is not configured. Set LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET "
            "(free 'Build' tier at cloud.livekit.io)."
        )
    try:
        from livekit import api
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("livekit-api not installed (pip install -e '.')") from exc

    ident = identity or f"tester-{uuid.uuid4().hex[:8]}"
    metadata = await _tenant_metadata(tenant)
    grants = api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True)
    builder = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(ident)
        .with_name(ident)
        .with_grants(grants)
    )
    if metadata:
        builder = builder.with_metadata(metadata)
    return TokenResponse(url=settings.LIVEKIT_URL, token=builder.to_jwt(), room=room, identity=ident)
