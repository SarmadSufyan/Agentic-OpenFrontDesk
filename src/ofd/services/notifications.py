"""Built-in email alerts: "email me every new lead / booking / call summary" without any automation tool.

Settings live in the workspace's `settings["notifications"]`:

    {"emails": ["owner@clinic.com"], "events": ["lead.created", "booking.created"]}

Alerts ride on the same committed-event pipeline as webhooks (`webhooks.emit`), so they only fire for
data that was actually saved, and they never block a request or a call.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from ofd.core.config import settings
from ofd.core.exceptions import ValidationError
from ofd.core.logging import get_logger
from ofd.schemas.contact import normalize_email
from ofd.services import mailer

logger = get_logger("ofd.services.notifications")

ALERT_EVENTS: dict[str, str] = {
    "lead.created": "New leads and messages",
    "booking.created": "New bookings",
    "call.completed": "Call summaries with the transcript",
}
MAX_RECIPIENTS = 5


def read_settings(tenant_settings: dict | None) -> dict:
    raw = (tenant_settings or {}).get("notifications") or {}
    return {
        "emails": [e for e in raw.get("emails", []) if isinstance(e, str)],
        "events": [e for e in raw.get("events", []) if e in ALERT_EVENTS],
    }


def validate(emails: list[str], events: list[str]) -> dict:
    cleaned: list[str] = []
    for e in emails:
        if not e or not e.strip():
            continue
        try:
            cleaned.append(normalize_email(e))
        except ValueError as exc:
            raise ValidationError(f"Not a valid email address: {e.strip()}") from exc
    cleaned = sorted(set(cleaned))
    if len(cleaned) > MAX_RECIPIENTS:
        raise ValidationError(f"Up to {MAX_RECIPIENTS} recipients are supported")
    unknown = [e for e in events if e not in ALERT_EVENTS]
    if unknown:
        raise ValidationError(f"Unknown alert type(s): {', '.join(unknown)}")
    return {"emails": cleaned, "events": sorted(set(events))}


# --------------------------------------------------------------------------- composing
def _local(iso: str | None, tz: str) -> str:
    if not iso:
        return "-"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.astimezone(ZoneInfo(tz or "UTC")).strftime("%a %d %b %Y, %H:%M")
    except Exception:
        return iso


def _link(path: str) -> str:
    return f"{settings.WEB_APP_URL.rstrip('/')}{path}"


def compose(event: str, data: dict, *, business: str, timezone: str) -> tuple[str, str]:
    """Return (subject, body) for an alert. Plain text, readable on a phone."""
    if event == "lead.created":
        who = data.get("name") or data.get("phone") or data.get("email") or "Someone"
        lines = [
            f"{who} left their details with your receptionist at {business}.",
            "",
            f"Name:     {data.get('name') or '-'}",
            f"Phone:    {data.get('phone') or '-'}",
            f"Email:    {data.get('email') or '-'}",
            f"Intent:   {data.get('intent') or '-'}",
            "",
            f"Message:\n{data.get('message') or '-'}",
            "",
            f"All leads: {_link('/dashboard/leads')}",
        ]
        return f"New lead: {who}", "\n".join(lines)

    if event == "booking.created":
        when = _local(data.get("start_at"), timezone)
        service = data.get("service") or "Appointment"
        lines = [
            f"Your receptionist booked an appointment at {business}.",
            "",
            f"When:      {when} ({timezone})",
            f"Service:   {service}",
            f"Customer:  {data.get('customer_name') or '-'}",
            f"Phone:     {data.get('customer_phone') or '-'}",
        ]
        if data.get("notes"):
            lines.append(f"Notes:     {data['notes']}")
        lines += ["", f"All bookings: {_link('/dashboard/bookings')}"]
        return f"New booking: {service}, {when}", "\n".join(lines)

    if event == "call.completed":
        seconds = int(data.get("duration_seconds") or 0)
        outcome = (data.get("outcome") or "completed").replace("_", " ")
        transcript = "\n".join(
            f"{'Receptionist' if t.get('role') in ('assistant', 'agent') else 'Caller'}: {t.get('text', '')}"
            for t in (data.get("transcript") or [])
        )
        lines = [
            f"A call to {business} just ended.",
            "",
            f"Started:   {_local(data.get('started_at'), timezone)}",
            f"Length:    {seconds // 60}:{seconds % 60:02d}",
            f"Outcome:   {outcome}",
            f"Caller:    {data.get('caller_number') or 'web caller'}",
        ]
        if data.get("summary"):
            lines += ["", f"Summary: {data['summary']}"]
        lines += ["", "Transcript", "----------", transcript or "(no transcript recorded)", ""]
        lines.append(f"All calls: {_link('/dashboard/conversations')}")
        return f"Call summary: {outcome} ({seconds // 60}:{seconds % 60:02d})", "\n".join(lines)

    raise ValueError(f"No alert template for {event}")


# --------------------------------------------------------------------------- sending
async def notify(tenant_id: uuid.UUID, event: str, data: dict) -> None:
    """Background task: email the workspace's alert recipients about `event`. Never raises."""
    if event not in ALERT_EVENTS or not mailer.is_configured():
        return
    from ofd.db.session import session_scope
    from ofd.models.tenant import Tenant

    try:
        async with session_scope() as db:
            tenant = await db.get(Tenant, tenant_id)
            if tenant is None:
                return
            prefs = read_settings(tenant.settings)
            business, timezone = tenant.name, tenant.timezone or "UTC"
        if event not in prefs["events"] or not prefs["emails"]:
            return
        subject, body = compose(event, data, business=business, timezone=timezone)
        await mailer.send(to=prefs["emails"], subject=f"{subject} - {business}", text=body)
    except Exception as exc:
        logger.warning("alert_failed", event=event, error=str(exc)[:300])


async def send_test(*, tenant_name: str, emails: list[str]) -> bool:
    if not emails:
        raise ValidationError("Add at least one recipient first")
    if not mailer.is_configured():
        raise ValidationError("Email sending is not configured on this server (SMTP_HOST)")
    return await mailer.send(
        to=emails,
        subject=f"Test alert - {tenant_name}",
        text=(
            f"This is a test alert from {settings.APP_NAME} for {tenant_name}.\n\n"
            "If you can read this, email alerts are working. You will get an email like this one "
            "whenever one of the events you chose happens.\n\n"
            f"Alert settings: {_link('/dashboard/integrations')}"
        ),
    )
