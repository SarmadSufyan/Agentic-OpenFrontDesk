"""Booking model (appointments created by the agent)."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from ofd.models.enums import BookingStatus


class Booking(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "booking"

    call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("call.id", ondelete="SET NULL"), index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent.id", ondelete="SET NULL")
    )
    customer_name: Mapped[str | None] = mapped_column(String(200))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    service: Mapped[str | None] = mapped_column(String(200))
    start_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=BookingStatus.CONFIRMED, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(200))  # Cal.com / Google id
    notes: Mapped[str | None] = mapped_column(Text)
