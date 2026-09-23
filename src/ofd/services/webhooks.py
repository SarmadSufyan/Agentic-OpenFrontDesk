"""Outbound webhooks: signed event notifications to a tenant's n8n / Zapier / custom endpoints.

Events are emitted fire-and-forget from the services that create data (leads, bookings, calls,
knowledge), so no request or live call waits on a slow receiver. Each delivery is:
- HMAC-SHA256 signed over "<timestamp>.<body>" (header X-OFD-Signature: sha256=<hex>),
- SSRF-guarded (private/internal hosts are refused unless WEBHOOK_ALLOW_PRIVATE is set; redirects
  are not followed),
- retried with backoff on network errors, 5xx, 408 and 429,
- logged to webhook_delivery; an endpoint auto-disables after repeated consecutive failures.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import time
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete as sa_delete
from sqlalchemy import event as sa_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ofd.core.config import settings
from ofd.core.exceptions import NotFound, ValidationError
from ofd.core.logging import get_logger
from ofd.models.automation import WebhookDelivery, WebhookEndpoint

logger = get_logger("ofd.services.webhooks")

EVENT_TYPES: dict[str, str] = {
    "lead.created": "A caller or website visitor left their details or a message.",
    "booking.created": "An appointment was booked by the voice agent or the chat widget.",
    "call.completed": "A voice call ended (outcome, duration, transcript).",
    "knowledge.ready": "A knowledge document finished indexing and is now searchable.",
}
TEST_EVENT = "webhook.test"
_RETRYABLE = {408, 429}
_PENDING_KEY = "ofd_pending_webhooks"

# Keep references to in-flight delivery tasks so they are not garbage-collected mid-flight.
_TASKS: set[asyncio.Task] = set()


# --------------------------------------------------------------------------- helpers
def generate_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(24)


def sign(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def is_blocked_ip(ip: str) -> bool:
    """True for addresses a public SaaS must never call (loopback, private, link-local, etc.)."""
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def check_url_syntax(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError("Webhook URL must be an http(s) URL with a host")
    return parsed.hostname


async def assert_deliverable(url: str, *, allow_private: bool | None = None) -> None:
    """Resolve the host and refuse private/internal targets (SSRF guard)."""
    host = check_url_syntax(url)
    allow = settings.WEBHOOK_ALLOW_PRIVATE if allow_private is None else allow_private
    if allow:
        return
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise ValidationError(f"Cannot resolve webhook host '{host}'") from exc
    for info in infos:
        if is_blocked_ip(info[4][0]):
            raise ValidationError(
                "Webhook URL points to a private or internal address. For a self-hosted receiver "
                "on your own network (e.g. n8n), set WEBHOOK_ALLOW_PRIVATE=true."
            )


def _normalize_events(events: list[str] | None) -> list[str]:
    events = [e.strip() for e in (events or []) if e and e.strip()]
    if not events or "*" in events:
        return ["*"]
    unknown = [e for e in events if e not in EVENT_TYPES]
    if unknown:
        raise ValidationError(f"Unknown event type(s): {', '.join(unknown)}")
    return sorted(set(events))


def _subscribed(ep: WebhookEndpoint, event: str) -> bool:
    evs = ep.events or ["*"]
    return event == TEST_EVENT or "*" in evs or event in evs


def _envelope(tenant_id: uuid.UUID, event: str, data: dict) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event,
        "created_at": datetime.now(UTC).isoformat(),
        "tenant_id": str(tenant_id),
        "data": data,
    }


# --------------------------------------------------------------------------- CRUD
async def create_endpoint(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    url: str,
    events: list[str] | None = None,
    description: str | None = None,
) -> WebhookEndpoint:
    await assert_deliverable(url)
    ep = WebhookEndpoint(
        tenant_id=tenant_id,
        url=url,
        description=description,
        events=_normalize_events(events),
        secret=generate_secret(),
        is_active=True,
    )
    db.add(ep)
    await db.flush()
    return ep


async def get_endpoint(
    db: AsyncSession, *, tenant_id: uuid.UUID, endpoint_id: uuid.UUID
) -> WebhookEndpoint:
    ep = await db.get(WebhookEndpoint, endpoint_id)
    if not ep or ep.tenant_id != tenant_id:
        raise NotFound("Webhook not found")
    return ep


async def list_endpoints(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[WebhookEndpoint]:
    stmt = (
        select(WebhookEndpoint)
        .where(WebhookEndpoint.tenant_id == tenant_id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def update_endpoint(
    db: AsyncSession, *, tenant_id: uuid.UUID, endpoint_id: uuid.UUID, data: dict
) -> WebhookEndpoint:
    ep = await get_endpoint(db, tenant_id=tenant_id, endpoint_id=endpoint_id)
    if data.get("url"):
        await assert_deliverable(data["url"])
        ep.url = data["url"]
    if "events" in data and data["events"] is not None:
        ep.events = _normalize_events(data["events"])
    if "description" in data:
        ep.description = data["description"]
    if data.get("is_active") is not None:
        ep.is_active = bool(data["is_active"])
        if ep.is_active:
            ep.failure_count = 0
    await db.flush()
    return ep


async def rotate_secret(
    db: AsyncSession, *, tenant_id: uuid.UUID, endpoint_id: uuid.UUID
) -> WebhookEndpoint:
    ep = await get_endpoint(db, tenant_id=tenant_id, endpoint_id=endpoint_id)
    ep.secret = generate_secret()
    await db.flush()
    return ep


async def delete_endpoint(
    db: AsyncSession, *, tenant_id: uuid.UUID, endpoint_id: uuid.UUID
) -> None:
    await get_endpoint(db, tenant_id=tenant_id, endpoint_id=endpoint_id)
    await db.execute(sa_delete(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id))
    await db.flush()


async def list_deliveries(
    db: AsyncSession, *, tenant_id: uuid.UUID, endpoint_id: uuid.UUID, limit: int = 50
) -> list[WebhookDelivery]:
    await get_endpoint(db, tenant_id=tenant_id, endpoint_id=endpoint_id)
    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.endpoint_id == endpoint_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# --------------------------------------------------------------------------- delivery
async def _deliver(db: AsyncSession, ep: WebhookEndpoint, envelope: dict) -> WebhookDelivery:
    body = json.dumps(envelope, default=str, separators=(",", ":")).encode()
    status_code: int | None = None
    error: str | None = None
    attempts = 0
    started = time.perf_counter()

    try:
        await assert_deliverable(ep.url)  # re-checked at send time, not only at creation
    except ValidationError as exc:
        error = str(exc)
    else:
        async with httpx.AsyncClient(
            timeout=settings.WEBHOOK_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            for attempt in range(1, max(1, settings.WEBHOOK_MAX_ATTEMPTS) + 1):
                attempts = attempt
                ts = int(time.time())
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "OpenFrontDesk-Webhooks/1.0",
                    "X-OFD-Event": envelope["type"],
                    "X-OFD-Delivery": envelope["id"],
                    "X-OFD-Timestamp": str(ts),
                    "X-OFD-Signature": sign(ep.secret, ts, body),
                }
                try:
                    resp = await client.post(ep.url, content=body, headers=headers)
                    status_code = resp.status_code
                    if 200 <= status_code < 300:
                        error = None
                        break
                    error = f"HTTP {status_code}"
                    if status_code < 500 and status_code not in _RETRYABLE:
                        break  # permanent client error; don't hammer the receiver
                except httpx.HTTPError as exc:
                    error = f"{type(exc).__name__}: {exc}"[:500]
                if attempt < settings.WEBHOOK_MAX_ATTEMPTS:
                    await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 8))

    success = error is None and status_code is not None and 200 <= status_code < 300
    delivery = WebhookDelivery(
        tenant_id=ep.tenant_id,
        endpoint_id=ep.id,
        event_id=envelope["id"],
        event=envelope["type"],
        success=success,
        status_code=status_code,
        attempts=max(attempts, 1),
        error=error,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    db.add(delivery)

    ep.last_status = status_code
    ep.last_delivery_at = datetime.now(UTC)
    if success:
        ep.failure_count = 0
    else:
        ep.failure_count = (ep.failure_count or 0) + 1
        if ep.failure_count >= settings.WEBHOOK_DISABLE_AFTER_FAILURES:
            ep.is_active = False
            logger.warning("webhook_auto_disabled", endpoint_id=str(ep.id))
    await db.flush()
    return delivery


async def _deliver_event(tenant_id: uuid.UUID, event: str, data: dict) -> None:
    from ofd.db.session import session_scope

    try:
        async with session_scope() as db:
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.tenant_id == tenant_id, WebhookEndpoint.is_active.is_(True)
            )
            endpoints = [ep for ep in (await db.execute(stmt)).scalars() if _subscribed(ep, event)]
            if not endpoints:
                return
            envelope = _envelope(tenant_id, event, data)
            for ep in endpoints:
                await _deliver(db, ep, envelope)
    except Exception as exc:  # background task: never raise
        logger.warning("webhook_emit_failed", event=event, error=str(exc))


def emit(tenant_id: uuid.UUID, event: str, data: dict) -> None:
    """Schedule delivery of `event` to the tenant's subscribed endpoints without waiting."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_deliver_event(tenant_id, event, data))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


def emit_on_commit(db: AsyncSession, tenant_id: uuid.UUID, event: str, data: dict) -> None:
    """Queue an event on the session; it is emitted only if the transaction commits.

    Services call this right after creating a row, so a rolled-back request never notifies
    receivers about data that does not exist.
    """
    db.info.setdefault(_PENDING_KEY, []).append((tenant_id, event, data))


@sa_event.listens_for(Session, "after_commit")
def _emit_pending(session: Session) -> None:
    for tenant_id, event, data in session.info.pop(_PENDING_KEY, []):
        emit(tenant_id, event, data)


@sa_event.listens_for(Session, "after_soft_rollback")
def _drop_pending(session: Session, previous_transaction) -> None:
    # Fires on every rollback, even one that never touched the DB; savepoint rollbacks leave the
    # outer transaction (and its queued events) alive.
    if not previous_transaction.nested:
        session.info.pop(_PENDING_KEY, None)


async def drain(wait_seconds: float = 10.0) -> None:
    """Wait for in-flight deliveries (used before a worker process shuts down)."""
    pending = [t for t in _TASKS if not t.done()]
    if pending:
        await asyncio.wait(pending, timeout=wait_seconds)


async def send_test(db: AsyncSession, ep: WebhookEndpoint) -> WebhookDelivery:
    envelope = _envelope(
        ep.tenant_id,
        TEST_EVENT,
        {"message": "Test delivery from OpenFrontDesk. Your endpoint is connected."},
    )
    return await _deliver(db, ep, envelope)
