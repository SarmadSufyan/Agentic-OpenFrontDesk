"""WhatsApp channel schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppConnectIn(BaseModel):
    base_url: str = Field(..., max_length=500)
    session_id: str = Field(..., min_length=1, max_length=120)
    api_key: str = Field(..., min_length=1, max_length=500)


class WhatsAppStatusOut(BaseModel):
    connected: bool
    provider: str | None = None
    base_url: str | None = None
    session_id: str | None = None
    api_key_hint: str | None = None
    phone: str | None = None
    inbound_url: str | None = None
    session_status: str | None = None  # the gateway's view: CONNECTED, DISCONNECTED, UNREACHABLE...
    session_error: str | None = None
    last_inbound_at: datetime | None = None
    last_error: str | None = None


class WhatsAppTestOut(BaseModel):
    success: bool
    status_code: int | None = None
    error: str | None = None


class ChannelMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contact: str
    contact_name: str | None = None
    direction: str
    text: str
    created_at: datetime
