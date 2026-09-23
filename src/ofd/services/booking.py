"""Booking service.

Default backend = **internal** calendar (free, no account): availability from the tenant's business
hours minus existing bookings. Optional Cal.com sync when CALENDAR_BACKEND=calcom. Bookings are always
recorded in our DB (source of truth for the dashboard). See docs/07-providers.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import Conflict, ValidationError
from ofd.core.logging import get_logger
from ofd.models.booking import Booking
from ofd.models.enums import BookingStatus
from ofd.models.tenant import Tenant
from ofd.services import webhooks

logger = get_logger("ofd.services.booking")

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DEFAULT_HOURS = {d: ["09:00", "17:00"] for d in ["mon", "tue", "wed", "thu", "fri"]}


@dataclass
class Slot:
    start: datetime
    end: datetime

    def iso(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


def _tz(tenant: Tenant) -> ZoneInfo:
    try:
        return ZoneInfo(tenant.timezone or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _hours_for(business_hours: dict, weekday: int) -> tuple[time, time] | None:
    hours = business_hours or _DEFAULT_HOURS
    spec = hours.get(_DAYS[weekday])
    if not spec:
        return None
    try:
        start = time.fromisoformat(spec[0])
        end = time.fromisoformat(spec[1])
        return start, end
    except Exception:
        return None


async def _existing(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime) -> bool:
    stmt = select(Booking.id).where(
        Booking.tenant_id == tenant_id,
        Booking.status == BookingStatus.CONFIRMED,
        Booking.start_at < end,
        Booking.end_at > start,
    )
    return (await db.execute(stmt)).first() is not None


async def check_availability(
    db: AsyncSession,
    tenant: Tenant,
    *,
    service: str | None = None,
    on_date: datetime | None = None,
    slot_minutes: int = 30,
    limit: int = 5,
    horizon_days: int = 14,
) -> list[Slot]:
    tz = _tz(tenant)
    now = datetime.now(tz)
    day0 = on_date.astimezone(tz).date() if on_date else now.date()
    out: list[Slot] = []

    for offset in range(0, horizon_days):
        day = day0 + timedelta(days=offset)
        hours = _hours_for(tenant.business_hours, day.weekday())
        if not hours:
            continue
        cursor = datetime.combine(day, hours[0], tzinfo=tz)
        end_of_day = datetime.combine(day, hours[1], tzinfo=tz)
        while cursor + timedelta(minutes=slot_minutes) <= end_of_day:
            slot_end = cursor + timedelta(minutes=slot_minutes)
            if cursor > now and not await _existing(db, tenant.id, cursor, slot_end):
                out.append(Slot(cursor, slot_end))
                if len(out) >= limit:
                    return out
            cursor = slot_end
        if on_date is not None:  # only the requested day
            break
    return out


async def book(
    db: AsyncSession,
    tenant: Tenant,
    *,
    name: str,
    phone: str,
    service: str | None,
    start_at: datetime,
    slot_minutes: int = 30,
    agent_id: uuid.UUID | None = None,
    call_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> Booking:
    tz = _tz(tenant)
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=tz)
    if start_at <= datetime.now(UTC):
        raise ValidationError("Requested time is in the past")

    end_at = start_at + timedelta(minutes=slot_minutes)
    if await _existing(db, tenant.id, start_at, end_at):
        raise Conflict("That time is no longer available")

    external_ref: str | None = None
    if settings.CALENDAR_BACKEND == "calcom":
        try:
            from ofd.services.calcom import CalcomClient

            event_type_id = int((tenant.settings or {}).get("calcom_event_type_id", 0))
            if event_type_id:
                res = await CalcomClient().create_booking(
                    event_type_id=event_type_id, start=start_at, name=name, phone=phone, notes=notes
                )
                external_ref = str(res.get("id") or res.get("uid") or "")
        except Exception as exc:  # keep internal booking as source of truth
            logger.warning("calcom_sync_failed", error=str(exc))

    booking = Booking(
        tenant_id=tenant.id,
        call_id=call_id,
        agent_id=agent_id,
        customer_name=name,
        customer_phone=phone,
        service=service,
        start_at=start_at,
        end_at=end_at,
        status=BookingStatus.CONFIRMED,
        external_ref=external_ref,
        notes=notes,
    )
    db.add(booking)
    await db.flush()
    webhooks.emit_on_commit(db, tenant.id, "booking.created", booking_payload(booking))
    return booking


def booking_payload(booking: Booking) -> dict:
    return {
        "id": str(booking.id),
        "customer_name": booking.customer_name,
        "customer_phone": booking.customer_phone,
        "service": booking.service,
        "start_at": booking.start_at.isoformat() if booking.start_at else None,
        "end_at": booking.end_at.isoformat() if booking.end_at else None,
        "status": booking.status,
        "notes": booking.notes,
        "call_id": str(booking.call_id) if booking.call_id else None,
        "agent_id": str(booking.agent_id) if booking.agent_id else None,
    }


async def cancel(db: AsyncSession, tenant_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
    booking = await db.get(Booking, booking_id)
    if not booking or booking.tenant_id != tenant_id:
        raise ValidationError("Booking not found")
    booking.status = BookingStatus.CANCELLED
    await db.flush()
    return booking


async def list_bookings(
    db: AsyncSession, *, tenant_id: uuid.UUID, limit: int = 100
) -> list[Booking]:
    stmt = (
        select(Booking)
        .where(Booking.tenant_id == tenant_id)
        .order_by(Booking.start_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
