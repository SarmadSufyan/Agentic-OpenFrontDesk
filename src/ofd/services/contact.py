"""Custom-solution requests: intake from the contact form, notifications, and the admin inbox.

Flow: a company describes what it needs (WhatsApp assistant, HR helpdesk, automations, ...), gets an
instant confirmation plus an optional self-serve booking link, and the admins are notified by email and
an optional webhook. Admins work the request in the inbox (status, notes, meeting) and can send a
personal scheduling email from there.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import NotFound, ValidationError
from ofd.core.logging import get_logger
from ofd.models.contact import ContactRequest
from ofd.schemas.contact import NEEDS, STATUSES, ContactIn
from ofd.services import mailer

logger = get_logger("ofd.services.contact")

_DEDUPE_WINDOW = timedelta(minutes=10)
_URL = re.compile(r"https?://", re.I)


# --------------------------------------------------------------------------- helpers
def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()


def looks_like_spam(body: ContactIn) -> bool:
    """Cheap heuristics on top of the honeypot: link-stuffed messages are almost always spam."""
    return len(_URL.findall(body.message)) > 4


def scheduling_link(name: str | None, email: str | None, base: str | None = None) -> str | None:
    """The booking link prefilled with the requester's details (Cal.com and Calendly both read
    `name` and `email` from the query string)."""
    base = base or settings.SCHEDULING_URL
    if not base:
        return None
    parts = urlparse(base)
    query = dict(parse_qsl(parts.query))
    if name:
        query.setdefault("name", name)
    if email:
        query.setdefault("email", email)
    return urlunparse(parts._replace(query=urlencode(query)))


def need_labels(needs: list[str]) -> str:
    return ", ".join(NEEDS.get(n, n) for n in needs) or "a custom setup"


def _summary_lines(req: ContactRequest) -> list[str]:
    return [
        f"Name:      {req.name}",
        f"Email:     {req.email}",
        f"Company:   {req.company or '-'}",
        f"Phone:     {req.phone or '-'}",
        f"Website:   {req.website or '-'}",
        f"Team size: {req.team_size or '-'}",
        f"Needs:     {need_labels(req.needs or [])}",
        f"Budget:    {req.budget or '-'}",
        f"Signed-in: {'yes' if req.user_id else 'no'}",
    ]


# --------------------------------------------------------------------------- intake
async def create_request(
    db: AsyncSession,
    body: ContactIn,
    *,
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[ContactRequest, bool]:
    """Store a request. Returns (request, is_new); a double-submit returns the earlier row."""
    since = datetime.now(UTC) - _DEDUPE_WINDOW
    existing = (
        await db.execute(
            select(ContactRequest)
            .where(
                ContactRequest.email == body.email,
                ContactRequest.message == body.message,
                ContactRequest.created_at >= since,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return existing, False

    req = ContactRequest(
        name=body.name,
        email=body.email,
        company=body.company or None,
        phone=body.phone or None,
        website=body.website or None,
        team_size=body.team_size,
        needs=body.needs,
        budget=body.budget,
        message=body.message,
        status="spam" if looks_like_spam(body) else "new",
        source=body.source or "contact_page",
        user_id=user_id,
        tenant_id=tenant_id,
        ip_hash=hash_ip(ip),
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(req)
    await db.flush()
    return req, True


async def notify_new_request(req_id: uuid.UUID) -> None:
    """Background task: tell the admins and confirm to the requester. Never raises."""
    from ofd.db.session import session_scope

    try:
        async with session_scope() as db:
            req = await db.get(ContactRequest, req_id)
            if req is None or req.status == "spam":
                return
            lines = _summary_lines(req)
            inbox = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/app#admin"
            admins = settings.contact_notify_emails

            if admins:
                await mailer.send(
                    to=admins,
                    subject=f"New custom-solution request: {req.company or req.name}",
                    text="\n".join(
                        [*lines, "", "Message:", req.message, "", f"Open the inbox: {inbox}"]
                    ),
                    reply_to=req.email,
                )

            link = scheduling_link(req.name, req.email)
            confirmation = [
                f"Hi {req.name.split()[0]},",
                "",
                f"Thanks for reaching out about {need_labels(req.needs or [])}. A member of our team "
                "reads every request personally and will reply within one business day to set up "
                "a call.",
            ]
            if link:
                confirmation += ["", "If you would rather pick a time right away:", link]
            confirmation += ["", f"The {settings.APP_NAME} team"]
            await mailer.send(
                to=req.email,
                subject=f"We received your request - {settings.APP_NAME}",
                text="\n".join(confirmation),
                reply_to=admins[0] if admins else None,
            )

            if settings.CONTACT_WEBHOOK_URL:
                await _post_webhook(req, inbox)
    except Exception as exc:
        logger.warning("contact_notify_failed", error=str(exc)[:300])


async def _post_webhook(req: ContactRequest, inbox: str) -> None:
    """Operator-configured hook (Slack incoming webhook, n8n, Zapier). `text` renders in Slack."""
    payload = {
        "text": f"New custom-solution request from {req.name}"
        f"{' (' + req.company + ')' if req.company else ''}: {need_labels(req.needs or [])}. "
        f"{inbox}",
        "event": "contact.created",
        "contact": {
            "id": str(req.id),
            "name": req.name,
            "email": req.email,
            "company": req.company,
            "phone": req.phone,
            "website": req.website,
            "team_size": req.team_size,
            "needs": req.needs or [],
            "budget": req.budget,
            "message": req.message,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.CONTACT_WEBHOOK_URL, json=payload)
            if resp.status_code >= 400:
                logger.warning("contact_webhook_status", status=resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("contact_webhook_failed", error=str(exc)[:300])


# --------------------------------------------------------------------------- admin inbox
async def list_requests(
    db: AsyncSession,
    *,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ContactRequest], int, dict[str, int]]:
    stmt = select(ContactRequest)
    if status:
        stmt = stmt.where(ContactRequest.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ContactRequest.name.ilike(like),
                ContactRequest.email.ilike(like),
                ContactRequest.company.ilike(like),
                ContactRequest.message.ilike(like),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(ContactRequest.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars()
    counts = {s: 0 for s in STATUSES}
    for s, n in (
        await db.execute(
            select(ContactRequest.status, func.count()).group_by(ContactRequest.status)
        )
    ).all():
        counts[s] = n
    return list(rows), int(total), counts


async def get_request(db: AsyncSession, req_id: uuid.UUID) -> ContactRequest:
    req = await db.get(ContactRequest, req_id)
    if req is None:
        raise NotFound("Request not found")
    return req


async def update_request(
    db: AsyncSession, req_id: uuid.UUID, data: dict, *, admin_email: str
) -> ContactRequest:
    req = await get_request(db, req_id)
    for field in ("status", "notes", "meeting_at", "meeting_link"):
        if field in data and not (field == "status" and data[field] is None):
            setattr(req, field, data[field])
    if data.get("meeting_at") and "status" not in data and req.status in ("new", "contacted"):
        req.status = "scheduled"
    req.handled_by = admin_email
    await db.flush()
    return req


async def delete_request(db: AsyncSession, req_id: uuid.UUID) -> None:
    await get_request(db, req_id)
    await db.execute(sa_delete(ContactRequest).where(ContactRequest.id == req_id))
    await db.flush()


async def send_scheduling_email(
    db: AsyncSession,
    req_id: uuid.UUID,
    *,
    admin_email: str,
    message: str | None = None,
    link: str | None = None,
) -> ContactRequest:
    """Email the requester a personal note with a booking link, and mark them as contacted."""
    req = await get_request(db, req_id)
    url = (
        scheduling_link(req.name, req.email, base=link)
        if (link or settings.SCHEDULING_URL)
        else None
    )
    if not url:
        raise ValidationError("No scheduling link: set SCHEDULING_URL or pass a link")
    if not mailer.is_configured():
        raise ValidationError("Email is not configured: set SMTP_HOST and SMTP_FROM")

    first = req.name.split()[0]
    body = (
        message.strip()
        if message
        else (
            f"Thanks again for your interest in {need_labels(req.needs or [])}"
            f"{' for ' + req.company if req.company else ''}. We would love to learn more about your "
            "setup and show you what is possible. Please pick a time that suits you:"
        )
    )
    text = "\n".join([f"Hi {first},", "", body, "", url, "", f"The {settings.APP_NAME} team"])
    sent = await mailer.send(
        to=req.email,
        subject=f"Let's schedule a call - {settings.APP_NAME}",
        text=text,
        reply_to=admin_email,
    )
    if not sent:
        raise ValidationError("The email could not be sent; check the SMTP settings and logs")

    req.last_contacted_at = datetime.now(UTC)
    req.handled_by = admin_email
    if req.status == "new":
        req.status = "contacted"
    await db.flush()
    return req
