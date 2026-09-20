"""Agent (configured receptionist) and phone number models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Agent(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "agent"

    name: Mapped[str] = mapped_column(String(120), default="Front Desk", nullable=False)
    voice: Mapped[str] = mapped_column(String(80), default="af_heart", nullable=False)
    greeting: Mapped[str] = mapped_column(
        String, default="Thanks for calling! How can I help you today?", nullable=False
    )
    tone: Mapped[str] = mapped_column(String(40), default="friendly", nullable=False)
    persona: Mapped[dict] = mapped_column(JSONB, default=dict)
    escalation_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    booking_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    llm_overrides: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PhoneNumber(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "phone_number"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent.id", ondelete="SET NULL")
    )
    e164: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), default="telnyx", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
