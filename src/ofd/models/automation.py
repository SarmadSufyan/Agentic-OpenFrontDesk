"""Automation models: outbound webhook endpoints, their delivery log, and tenant API keys."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class WebhookEndpoint(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """A URL that receives signed event notifications (e.g. an n8n or Zapier webhook)."""

    __tablename__ = "webhook_endpoint"

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    events: Mapped[list] = mapped_column(JSONB, default=list)  # subscribed event types
    secret: Mapped[str] = mapped_column(String(128), nullable=False)  # HMAC signing secret
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_status: Mapped[int | None] = mapped_column(Integer)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookDelivery(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """One delivery attempt outcome, kept for debugging and the dashboard."""

    __tablename__ = "webhook_delivery"

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("webhook_endpoint.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ApiKey(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """A tenant API key for integrations. Only a SHA-256 hash is stored; the key is shown once."""

    __tablename__ = "api_key"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # shown in the UI
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="SET NULL")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
