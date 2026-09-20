"""Thin Cal.com API client (used only when CALENDAR_BACKEND=calcom).

Cal.com is the open-source scheduler. Endpoints/versions evolve — verify against your Cal.com API
version (docs/07-providers.md). The internal calendar backend (default) needs none of this.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from ofd.core.config import settings
from ofd.core.exceptions import ConfigError, ProviderError


class CalcomClient:
    def __init__(self) -> None:
        if not settings.CALCOM_API_KEY:
            raise ConfigError("CALCOM_API_KEY not set")
        self.base = settings.CALCOM_BASE_URL.rstrip("/")
        self.key = settings.CALCOM_API_KEY

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    async def create_booking(
        self, *, event_type_id: int, start: datetime, name: str, phone: str, notes: str | None = None
    ) -> dict:
        payload = {
            "eventTypeId": event_type_id,
            "start": start.isoformat(),
            "responses": {"name": name, "phone": phone, "notes": notes or ""},
            "timeZone": settings.__dict__.get("timezone", "UTC"),
            "language": "en",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base}/bookings", json=payload, headers=self._headers()
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:  # pragma: no cover
            raise ProviderError(f"Cal.com booking failed: {exc}") from exc
