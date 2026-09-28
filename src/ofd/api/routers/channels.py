"""WhatsApp channel API: connect a gateway, check it, read conversations, and receive messages.

Management endpoints are for workspace owners and admins. The inbound endpoint is public but only
accepts events signed with the connection's secret; it acknowledges at once and answers in the
background, so the gateway's 10-second timeout is never at risk while the model thinks.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import AuthContext, get_db, require_roles
from ofd.core.exceptions import NotFound, TooManyRequests, Unauthorized
from ofd.models.channel import WhatsAppConnection
from ofd.schemas.channel import (
    ChannelMessageOut,
    WhatsAppConnectIn,
    WhatsAppStatusOut,
    WhatsAppTestOut,
)
from ofd.services import audit as audit_svc
from ofd.services import quota as quota_svc
from ofd.services import whatsapp as wa_svc

router = APIRouter(prefix="/channels/whatsapp", tags=["channels"])
managers = require_roles("owner", "admin")


def _status(conn: WhatsAppConnection | None, live: dict | None = None) -> WhatsAppStatusOut:
    if conn is None:
        return WhatsAppStatusOut(connected=False)
    live = live or {}
    return WhatsAppStatusOut(
        connected=True,
        provider=conn.provider,
        base_url=conn.base_url,
        session_id=conn.session_id,
        api_key_hint=conn.api_key_hint,
        phone=conn.phone or wa_svc.me_phone(live),
        inbound_url=wa_svc.inbound_url(conn.id),
        session_status=live.get("status"),
        session_error=live.get("error"),
        last_inbound_at=conn.last_inbound_at,
        last_error=conn.last_error,
    )


@router.get("", response_model=WhatsAppStatusOut)
async def whatsapp_status(ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)):
    conn = await wa_svc.get_connection(db, ctx.tenant.id)
    return _status(conn, await wa_svc.live_status(conn) if conn else None)


@router.put("", response_model=WhatsAppStatusOut)
async def whatsapp_connect(
    body: WhatsAppConnectIn,
    ctx: AuthContext = Depends(managers),
    db: AsyncSession = Depends(get_db),
):
    conn, info = await wa_svc.connect(
        db, ctx.tenant, base_url=body.base_url, session_id=body.session_id, api_key=body.api_key
    )
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="whatsapp.connect",
        target=f"{conn.base_url} / {conn.session_id}",
    )
    return _status(conn, {"status": info.get("status"), "me": info.get("me")})


@router.delete("", status_code=204)
async def whatsapp_disconnect(
    ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
) -> None:
    await wa_svc.disconnect(db, ctx.tenant.id)
    await audit_svc.record(
        db, tenant_id=ctx.tenant.id, actor_user_id=ctx.user.id, action="whatsapp.disconnect"
    )


@router.post("/test", response_model=WhatsAppTestOut)
async def whatsapp_test(ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)):
    conn = await wa_svc.get_connection(db, ctx.tenant.id)
    if conn is None:
        raise NotFound("WhatsApp is not connected")
    return await wa_svc.test_connection(conn)


@router.get("/messages", response_model=list[ChannelMessageOut])
async def whatsapp_messages(
    limit: int = Query(100, ge=1, le=500),
    ctx: AuthContext = Depends(managers),
    db: AsyncSession = Depends(get_db),
):
    return await wa_svc.recent_messages(db, ctx.tenant.id, limit=limit)


@router.post("/inbound/{connection_id}", include_in_schema=False)
async def whatsapp_inbound(
    connection_id: uuid.UUID,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conn = await db.get(WhatsAppConnection, connection_id)
    if conn is None or not conn.is_active:
        raise NotFound("Unknown channel")
    raw = await request.body()
    if not wa_svc.verify_signature(
        conn.webhook_secret, raw, request.headers.get("x-webhook-signature")
    ):
        raise Unauthorized("Invalid signature")
    allowed, _ = await quota_svc.hit(f"wa-inbound:{connection_id}", 300, 60)
    if not allowed:
        raise TooManyRequests("Too many events")
    try:
        payload = json.loads(raw)
    except ValueError:
        return {"ok": False, "reason": "not json"}
    if payload.get("event") == "test":
        return {"ok": True, "test": True}
    background.add_task(wa_svc.handle_inbound, connection_id, payload)
    return {"ok": True}
