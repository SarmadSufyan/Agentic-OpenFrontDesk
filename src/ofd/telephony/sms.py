"""SMS provider abstraction (confirmations / follow-ups).

Default `none` -> no-op (logs what would be sent) so the demo works with zero config. Twilio/Telnyx
imported lazily. Sending is best-effort and should be enqueued off the hot call path (Phase 4 jobs).
"""

from __future__ import annotations

from dataclasses import dataclass

from ofd.core.config import settings
from ofd.core.logging import get_logger

logger = get_logger("ofd.telephony.sms")


@dataclass
class SMSResult:
    status: str
    provider: str
    detail: str | None = None


class NoopSMS:
    provider = "none"

    async def send(self, to: str, body: str) -> SMSResult:
        logger.info("sms_skipped", to=to, body=body[:120], reason="SMS_PROVIDER=none")
        return SMSResult(status="skipped", provider=self.provider, detail="SMS not configured")


class TwilioSMS:
    provider = "twilio"

    async def send(self, to: str, body: str) -> SMSResult:
        import asyncio

        def _do() -> str:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            msg = client.messages.create(to=to, from_=settings.TWILIO_ACCOUNT_SID, body=body)
            return msg.sid

        sid = await asyncio.to_thread(_do)
        return SMSResult(status="sent", provider=self.provider, detail=sid)


def get_sms_provider():
    if settings.SMS_PROVIDER == "twilio":
        return TwilioSMS()
    return NoopSMS()


async def send_sms(to: str, body: str) -> SMSResult:
    return await get_sms_provider().send(to, body)
