"""Call / booking / lead / analytics read schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    direction: str
    status: str
    outcome: str | None = None
    caller_number: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int
    cost_cents: int
    created_at: datetime


class CallDetailOut(CallOut):
    transcript: list = []
    summary: str | None = None
    latency_ms: dict = {}


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_name: str | None = None
    customer_phone: str | None = None
    service: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    status: str
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    intent: str | None = None
    message: str | None = None
    created_at: datetime


class AnalyticsOut(BaseModel):
    calls_total: int
    calls_by_outcome: dict[str, int]
    bookings_total: int
    leads_total: int
    minutes_total: float
    avg_latency_ms: float | None = None
