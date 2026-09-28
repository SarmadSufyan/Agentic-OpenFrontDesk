"""Messaging channels beyond voice and the website widget (currently WhatsApp)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class WhatsAppConnection(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """A workspace's link to a WhatsApp gateway. One per workspace.

    `provider` is "wa_akg" (a self-hosted WA-AKG gateway) today; the official WhatsApp Business Cloud API
    can be added as another provider behind the same model.
    """

    __tablename__ = "whatsapp_connection"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_whatsapp_connection_tenant"),)

    provider: Mapped[str] = mapped_column(String(20), default="wa_akg", nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    session_id: Mapped[str] = mapped_column(String(120), nullable=False)
    api_key_enc: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted at rest
    api_key_hint: Mapped[str] = mapped_column(String(8), nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String(128), nullable=False)
    remote_webhook_id: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))  # the connected WhatsApp number
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class ChannelMessage(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """One message in or out on a channel, kept so the business can read its WhatsApp conversations."""

    __tablename__ = "channel_message"

    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    contact: Mapped[str] = mapped_column(String(40), index=True, nullable=False)  # phone digits
    contact_name: Mapped[str | None] = mapped_column(String(200))
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # "in" | "out"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120))
