"""WhatsApp channel: the workspace's AI receptionist answers WhatsApp messages.

Provider today: a self-hosted **WA-AKG** gateway (https://github.com/mrifqidaffaaditya/WA-AKG), which
links a normal WhatsApp number the way WhatsApp Web does (unofficial; see docs/21-whatsapp.md for the
trade-offs). The flow:

1. Connect: the owner gives the gateway address, session id and API key. We check the session, then
   register a signed webhook on the gateway that points at our inbound URL.
2. Inbound: the gateway POSTs `message.received` events, signed with HMAC-SHA256 over the body
   (`X-Webhook-Signature: sha256=<hex>`). We verify, acknowledge immediately, and process in the
   background: filter, de-duplicate, rate-limit, answer with the same grounded chat brain as the website
   widget (with per-customer memory), send the reply through the gateway, and log both messages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlparse

import httpx
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import NotFound, ProviderError, ValidationError
from ofd.core.logging import get_logger
from ofd.models.channel import ChannelMessage, WhatsAppConnection
from ofd.models.tenant import Tenant
from ofd.services import quota as quota_svc
from ofd.services import secretbox, webhooks

logger = get_logger("ofd.services.whatsapp")

MAX_EVENT_AGE = timedelta(minutes=10)  # replay protection on top of the signature
HISTORY_TTL_SECONDS = 24 * 3600
TEXT_ONLY_REPLY = "Thanks for your message! I can only read text here at the moment. Could you type your question?"
_MEDIA_TYPES = {"IMAGE", "VIDEO", "DOCUMENT"}  # answered from their caption, if any
_UNREADABLE = {"AUDIO"}  # we ask the customer to type instead


# --------------------------------------------------------------------------- gateway client
class WaAkgClient:
    """Minimal client for the WA-AKG REST API (auth header: X-API-Key)."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.base = base_url.rstrip("/")
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self.timeout = timeout

    async def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                resp = await client.request(
                    method, f"{self.base}{path}", headers=self.headers, json=body
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Cannot reach the WhatsApp gateway at {self.base}: {exc}") from exc
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code in (401, 403):
            raise ValidationError(
                "The WhatsApp gateway rejected the API key, or it cannot use this session"
            )
        if resp.status_code == 404:
            raise ValidationError(data.get("message") or "Not found on the WhatsApp gateway")
        if resp.status_code >= 400 or data.get("status") is False:
            raise ProviderError(
                f"WhatsApp gateway error: {data.get('message') or resp.status_code}"
            )
        return data.get("data") if isinstance(data.get("data"), (dict, list)) else data

    async def session(self, session_id: str) -> dict:
        return await self._call("GET", f"/api/sessions/{quote(session_id, safe='')}")

    async def register_webhook(self, session_id: str, *, name: str, url: str, secret: str) -> dict:
        return await self._call(
            "POST",
            f"/api/webhooks/{quote(session_id, safe='')}",
            {"name": name, "url": url, "secret": secret, "events": ["message.received"]},
        )

    async def delete_webhook(self, session_id: str, webhook_id: str) -> None:
        await self._call(
            "DELETE", f"/api/webhooks/{quote(session_id, safe='')}/{quote(webhook_id, safe='')}"
        )

    async def test_webhook(self, session_id: str, webhook_id: str) -> dict:
        return await self._call(
            "POST", f"/api/webhooks/{quote(session_id, safe='')}/{quote(webhook_id, safe='')}/test"
        )

    async def send_text(self, session_id: str, jid: str, text: str) -> dict:
        return await self._call(
            "POST",
            f"/api/messages/{quote(session_id, safe='')}/{quote(jid, safe='')}/send",
            {"message": {"text": text}},
        )


def client_for(conn: WhatsAppConnection) -> WaAkgClient:
    return WaAkgClient(conn.base_url, secretbox.decrypt(conn.api_key_enc))


# --------------------------------------------------------------------------- helpers
def gateway_base(url: str) -> str:
    """Accept the gateway address with or without a trailing slash or /api suffix."""
    url = (url or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError("Enter the gateway address, starting with http:// or https://")
    return url[:-4] if url.endswith("/api") else url


def inbound_url(connection_id: uuid.UUID) -> str:
    return f"{settings.inbound_base_url}/channels/whatsapp/inbound/{connection_id}"


def verify_signature(secret: str, raw_body: bytes, header: str | None) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return bool(header) and hmac.compare_digest(expected, header.strip())


def phone_digits(jid: str | None) -> str | None:
    """'6281234567@s.whatsapp.net' -> '6281234567'. Other address kinds (groups, lids) -> None."""
    if not jid or not jid.endswith("@s.whatsapp.net"):
        return None
    digits = jid.split("@", 1)[0].split(":", 1)[0]
    return digits if digits.isdigit() else None


def me_phone(info: dict | None) -> str | None:
    """The gateway's own number from its session info: me.id looks like '6281234567:12@s.whatsapp.net'."""
    me_id = ((info or {}).get("me") or {}).get("id") or ""
    digits = me_id.split("@", 1)[0].split(":", 1)[0]
    return digits if digits.isdigit() else None


# --------------------------------------------------------------------------- connection lifecycle
async def get_connection(db: AsyncSession, tenant_id: uuid.UUID) -> WhatsAppConnection | None:
    stmt = select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def connect(
    db: AsyncSession, tenant: Tenant, *, base_url: str, session_id: str, api_key: str
) -> tuple[WhatsAppConnection, dict]:
    base = gateway_base(base_url)
    session_id = session_id.strip()
    api_key = api_key.strip()
    if not session_id or not api_key:
        raise ValidationError("Session ID and API key are both required")
    await webhooks.assert_deliverable(
        base
    )  # SSRF guard (private hosts only with WEBHOOK_ALLOW_PRIVATE)

    client = WaAkgClient(base, api_key)
    info = await client.session(session_id)  # proves the address, key and session are right

    conn = await get_connection(db, tenant.id)
    if conn is not None and conn.remote_webhook_id:
        try:  # detach the previous registration so the old session stops calling us
            await client_for(conn).delete_webhook(conn.session_id, conn.remote_webhook_id)
        except Exception as exc:
            logger.info("whatsapp_old_webhook_not_removed", error=str(exc)[:200])
    if conn is None:
        conn = WhatsAppConnection(tenant_id=tenant.id)
        db.add(conn)
    conn.provider = "wa_akg"
    conn.base_url = base
    conn.session_id = session_id
    conn.api_key_enc = secretbox.encrypt(api_key)
    conn.api_key_hint = api_key[-4:]
    conn.webhook_secret = "whsec_" + secrets.token_urlsafe(24)
    conn.is_active = True
    conn.last_error = None
    conn.phone = me_phone(info)
    await db.flush()  # the connection id is part of the inbound URL

    hook = await client.register_webhook(
        session_id,
        name=f"OpenFrontDesk ({tenant.name})",
        url=inbound_url(conn.id),
        secret=conn.webhook_secret,
    )
    conn.remote_webhook_id = (
        str(hook.get("id")) if isinstance(hook, dict) and hook.get("id") else None
    )
    await db.flush()
    return conn, info


async def disconnect(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    conn = await get_connection(db, tenant_id)
    if conn is None:
        raise NotFound("WhatsApp is not connected")
    if conn.remote_webhook_id:
        try:
            await client_for(conn).delete_webhook(conn.session_id, conn.remote_webhook_id)
        except Exception as exc:  # the gateway may be gone already; disconnecting must still work
            logger.info("whatsapp_webhook_not_removed", error=str(exc)[:200])
    await db.execute(sa_delete(WhatsAppConnection).where(WhatsAppConnection.id == conn.id))
    await db.flush()


async def live_status(conn: WhatsAppConnection) -> dict:
    """The gateway's view of the session: {"status": "CONNECTED", "me": {...}} or an error."""
    try:
        info = await client_for(conn).session(conn.session_id)
        return {"status": info.get("status") or "UNKNOWN", "me": info.get("me"), "error": None}
    except Exception as exc:
        return {"status": "UNREACHABLE", "me": None, "error": str(exc)[:300]}


async def test_connection(conn: WhatsAppConnection) -> dict:
    """Ask the gateway to deliver a signed test event to our inbound URL (proves both directions)."""
    if not conn.remote_webhook_id:
        raise ValidationError("The gateway webhook is missing. Connect WhatsApp again.")
    result = await client_for(conn).test_webhook(conn.session_id, conn.remote_webhook_id)
    return {
        "success": bool(result.get("success")),
        "status_code": result.get("statusCode"),
        "error": result.get("error"),
    }


async def recent_messages(db: AsyncSession, tenant_id: uuid.UUID, limit: int = 100) -> list:
    stmt = (
        select(ChannelMessage)
        .where(ChannelMessage.tenant_id == tenant_id, ChannelMessage.channel == "whatsapp")
        .order_by(ChannelMessage.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# --------------------------------------------------------------------------- inbound processing
def parse_inbound(payload: dict) -> dict | None:
    """Reduce a gateway event to what we answer, or None when it should be ignored."""
    if payload.get("event") != "message.received":
        return None
    data = payload.get("data") or {}
    key = data.get("key") or {}
    if key.get("fromMe") or data.get("isGroup") or data.get("chatType") not in (None, "PERSONAL"):
        return None
    phone = phone_digits(data.get("from"))
    if not phone:
        return None
    try:
        sent_at = datetime.fromisoformat(str(payload.get("timestamp")).replace("Z", "+00:00"))
        if datetime.now(UTC) - sent_at > MAX_EVENT_AGE:
            return None
    except ValueError:
        return None
    kind = (data.get("type") or "").upper()
    text = (data.get("content") or data.get("caption") or "").strip()
    if kind == "TEXT" or (kind in _MEDIA_TYPES and text):
        mode = "answer"
    elif kind in _UNREADABLE or kind in _MEDIA_TYPES:
        mode = "text_only"
    else:
        return None  # stickers, reactions, locations, contacts
    return {
        "mode": mode,
        "text": text[:4000],
        "phone": phone,
        "jid": data.get("from"),
        "name": (data.get("pushName") or "").strip()[:200] or None,
        "message_id": key.get("id"),
    }


async def _redis():
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _first_time(conn_id: uuid.UUID, message_id: str | None) -> bool:
    if not message_id:
        return True
    r = await _redis()
    try:
        return bool(await r.set(f"wa:seen:{conn_id}:{message_id}", "1", nx=True, ex=86400))
    except Exception:
        return True  # Redis down: answering twice beats not answering
    finally:
        await r.aclose()


async def _history(tenant_id: uuid.UUID, phone: str) -> list[dict]:
    r = await _redis()
    try:
        raw = await r.lrange(
            f"wa:hist:{tenant_id}:{phone}", -2 * settings.WHATSAPP_HISTORY_TURNS, -1
        )
        return [json.loads(x) for x in raw]
    except Exception:
        return []
    finally:
        await r.aclose()


async def _remember(tenant_id: uuid.UUID, phone: str, *turns: dict) -> None:
    r = await _redis()
    key = f"wa:hist:{tenant_id}:{phone}"
    try:
        await r.rpush(key, *[json.dumps(t) for t in turns])
        await r.ltrim(key, -2 * settings.WHATSAPP_HISTORY_TURNS, -1)
        await r.expire(key, HISTORY_TTL_SECONDS)
    except Exception:
        pass
    finally:
        await r.aclose()


async def handle_inbound(connection_id: uuid.UUID, payload: dict) -> None:
    """Background task: answer one inbound WhatsApp message. Never raises."""
    from ofd.db.session import session_scope
    from ofd.services import chat as chat_svc
    from ofd.services import tenants as tenants_svc

    msg = parse_inbound(payload)
    if msg is None or not await _first_time(connection_id, msg["message_id"]):
        return
    try:
        async with session_scope() as db:
            conn = await db.get(WhatsAppConnection, connection_id)
            if conn is None or not conn.is_active:
                return
            tenant = await db.get(Tenant, conn.tenant_id)
            if tenant is None:
                return
            conn.last_inbound_at = datetime.now(UTC)
            db.add(
                ChannelMessage(
                    tenant_id=tenant.id,
                    contact=msg["phone"],
                    contact_name=msg["name"],
                    direction="in",
                    text=msg["text"] or f"[{payload.get('data', {}).get('type', 'media').lower()}]",
                    external_id=msg["message_id"],
                    # explicit times: the database default is the transaction start, which would give
                    # the question and its answer the same timestamp and an unstable order
                    created_at=datetime.now(UTC),
                )
            )

            allowed, _ = await quota_svc.hit(
                f"wa:{tenant.id}:{msg['phone']}", settings.WHATSAPP_MAX_PER_SENDER_PER_10MIN, 600
            )
            if not allowed:
                logger.info("whatsapp_sender_rate_limited", tenant=str(tenant.id))
                return

            if msg["mode"] == "text_only":
                reply = TEXT_ONLY_REPLY
            else:
                agent = await tenants_svc.get_default_agent(db, tenant.id)
                history = await _history(tenant.id, msg["phone"])
                context = (
                    f"Channel: WhatsApp. The customer's WhatsApp number is +{msg['phone']}"
                    + (f" and their WhatsApp name is {msg['name']}" if msg["name"] else "")
                    + ". Use this number for bookings and messages unless they give another one."
                    " Keep replies short, like a text message, and do not use markdown."
                )
                result = await chat_svc.chat(
                    db,
                    tenant=tenant,
                    agent=agent,
                    message=msg["text"],
                    history=history,
                    context=context,
                )
                reply = (result.get("reply") or "").strip() or TEXT_ONLY_REPLY
                await _remember(
                    tenant.id,
                    msg["phone"],
                    {"role": "user", "content": msg["text"]},
                    {"role": "assistant", "content": reply},
                )

            try:
                await client_for(conn).send_text(conn.session_id, msg["jid"], reply)
                conn.last_error = None
            except Exception as exc:
                conn.last_error = f"Reply not sent: {exc}"[:500]
                logger.warning("whatsapp_send_failed", error=str(exc)[:300])
                return
            db.add(
                ChannelMessage(
                    tenant_id=tenant.id,
                    contact=msg["phone"],
                    contact_name=msg["name"],
                    direction="out",
                    text=reply,
                    created_at=datetime.now(UTC),
                )
            )
    except Exception as exc:
        logger.warning("whatsapp_inbound_failed", error=str(exc)[:300])
