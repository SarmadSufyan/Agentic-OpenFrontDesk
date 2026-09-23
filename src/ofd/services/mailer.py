"""Outbound email over SMTP (stdlib smtplib, run in a worker thread).

Email is optional: with SMTP_HOST unset, `send` logs and returns False, and every feature that uses it
keeps working (contact requests are still stored and visible in the admin inbox). Works with any SMTP
provider (Gmail app password, Brevo, Resend, SES, Postmark) and with Mailpit for local development.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr

from ofd.core.config import settings
from ofd.core.logging import get_logger

logger = get_logger("ofd.services.mailer")


def is_configured() -> bool:
    return bool(settings.SMTP_HOST and _sender())


def _sender() -> str:
    if settings.SMTP_FROM:
        return settings.SMTP_FROM
    if settings.SMTP_USER and "@" in settings.SMTP_USER:
        return formataddr((settings.APP_NAME, settings.SMTP_USER))
    return ""


def build_message(
    *, to: list[str], subject: str, text: str, reply_to: str | None = None
) -> EmailMessage:
    msg = EmailMessage()
    sender = _sender()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    domain = parseaddr(sender)[1].partition("@")[2] or None
    msg["Message-ID"] = make_msgid(domain=domain)
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)
    return msg


def _deliver(msg: EmailMessage) -> None:
    timeout = 15
    if settings.SMTP_SSL:
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    else:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout)
    with smtp:
        if settings.SMTP_STARTTLS and not settings.SMTP_SSL:
            smtp.starttls(context=ssl.create_default_context())
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send(
    *, to: list[str] | str, subject: str, text: str, reply_to: str | None = None
) -> bool:
    """Send a plain-text email. Returns True on success; never raises."""
    recipients = [to] if isinstance(to, str) else [t for t in to if t]
    if not recipients:
        return False
    if not is_configured():
        logger.info("email_skipped_not_configured", subject=subject)
        return False
    msg = build_message(to=recipients, subject=subject, text=text, reply_to=reply_to)
    try:
        await asyncio.to_thread(_deliver, msg)
        logger.info("email_sent", subject=subject, recipients=len(recipients))
        return True
    except Exception as exc:
        logger.warning("email_failed", subject=subject, error=str(exc)[:300])
        return False
