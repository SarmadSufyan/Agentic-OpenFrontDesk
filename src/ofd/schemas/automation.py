"""Automation schemas: webhooks, deliveries, API keys, and the public /v1 API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- webhooks
class WebhookIn(BaseModel):
    url: str = Field(..., max_length=2048)
    events: list[str] = Field(default_factory=lambda: ["*"])
    description: str | None = Field(None, max_length=200)


class WebhookUpdate(BaseModel):
    url: str | None = Field(None, max_length=2048)
    events: list[str] | None = None
    description: str | None = Field(None, max_length=200)
    is_active: bool | None = None


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    url: str
    description: str | None = None
    events: list[str]
    is_active: bool
    failure_count: int
    last_status: int | None = None
    last_delivery_at: datetime | None = None
    created_at: datetime
    secret_hint: str = ""

    @classmethod
    def of(cls, ep) -> WebhookOut:
        out = cls.model_validate(ep)
        out.secret_hint = "whsec_..." + (ep.secret or "")[-4:]
        return out


class WebhookWithSecret(WebhookOut):
    """Returned only on create and secret rotation, the one time the signing secret is shown."""

    secret: str


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_id: str
    event: str
    success: bool
    status_code: int | None = None
    attempts: int
    error: str | None = None
    duration_ms: int | None = None
    created_at: datetime


class EventTypeOut(BaseModel):
    type: str
    description: str


# --------------------------------------------------------------------------- API keys
class ApiKeyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    prefix: str
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    """Returned once at creation; the plaintext key is never retrievable again."""

    key: str


# --------------------------------------------------------------------------- public API
class MeOut(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    workspace_slug: str
    key_name: str


class ApiChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] | None = None


class ApiChatOut(BaseModel):
    reply: str
    sources: list[str] = []


class ApiLeadIn(BaseModel):
    name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=320)
    intent: str | None = Field(None, max_length=200)
    message: str | None = Field(None, max_length=5000)
    tags: list[str] = Field(default_factory=list)


class ApiBookingIn(BaseModel):
    name: str = Field(..., max_length=200)
    phone: str = Field(..., max_length=20)
    start_at: datetime
    service: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=2000)
    slot_minutes: int = Field(30, ge=5, le=480)


class SlotOut(BaseModel):
    start: datetime
    end: datetime
