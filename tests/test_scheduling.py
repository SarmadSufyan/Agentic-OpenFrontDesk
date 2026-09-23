"""Regression tests for date handling in scheduling and in the chat brain's prompt."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from ofd.services import booking, chat


def _tenant(tz: str, hours: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id="t1", name="Lotus Physio Studio", timezone=tz, business_hours=hours, settings={}
    )


async def _never_booked(*_args, **_kwargs) -> bool:
    return False


@pytest.mark.parametrize("tz", ["America/Los_Angeles", "UTC", "Asia/Karachi", "Pacific/Auckland"])
async def test_bare_date_means_that_day_where_the_business_is(
    tz: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare 'Sunday' must stay Sunday in every time zone (it used to shift west of UTC)."""
    monkeypatch.setattr(booking, "_existing", _never_booked)
    today = datetime.now(ZoneInfo(tz)).date()
    sunday = today + timedelta(days=(6 - today.weekday()) % 7 + 7)  # a Sunday next week
    tenant = _tenant(tz, {"sun": ["10:00", "14:00"]})

    slots = await booking.check_availability(
        None,  # type: ignore[arg-type]  # _existing is stubbed, so no DB is used
        tenant,  # type: ignore[arg-type]
        on_date=datetime.fromisoformat(sunday.isoformat()),
        slot_minutes=45,
        limit=10,
    )

    assert slots, "Sunday is open 10:00-14:00, so there must be slots"
    assert {s.start.date() for s in slots} == {sunday}
    assert slots[0].start.hour == 10 and str(slots[0].start.tzinfo) == tz


async def test_closed_day_returns_no_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking, "_existing", _never_booked)
    tz = "America/New_York"
    today = datetime.now(ZoneInfo(tz)).date()
    sunday = today + timedelta(days=(6 - today.weekday()) % 7 + 7)
    tenant = _tenant(tz, {"mon": ["09:00", "17:00"]})
    slots = await booking.check_availability(
        None,  # type: ignore[arg-type]
        tenant,  # type: ignore[arg-type]
        on_date=datetime.fromisoformat(sunday.isoformat()),
    )
    assert slots == []


def test_chat_prompt_knows_today_hours_and_tone() -> None:
    tenant = _tenant(
        "Asia/Karachi", {"mon": ["09:00", "18:00"], "sun": ["10:00", "14:00"], "tue": None}
    )
    agent = SimpleNamespace(
        tone="upbeat and energetic",
        booking_rules={"slot_minutes": 45, "services": ["Sports massage", "Follow-up session"]},
    )
    prompt = chat._system_prompt(tenant, agent)  # type: ignore[arg-type]
    today = datetime.now(ZoneInfo("Asia/Karachi"))
    assert today.strftime("%Y-%m-%d") in prompt and "Asia/Karachi" in prompt
    assert "upbeat and energetic" in prompt
    hours_line = next(line for line in prompt.splitlines() if line.startswith("Opening hours:"))
    assert "Mon 09:00-18:00" in hours_line and "Sun 10:00-14:00" in hours_line
    assert "Tue" not in hours_line  # closed days are not listed as open
    tomorrow = today + timedelta(days=1)
    assert f"{tomorrow:%a %Y-%m-%d}" in prompt  # the ready-made calendar
    assert "Sports massage" in prompt and "45 minutes" in prompt
