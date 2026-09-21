"""Call and call-event (turn-level) models."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from ofd.models.enums import CallDirection, CallStatus


class Call(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "call"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent.id", ondelete="SET NULL"), index=True
    )
    direction: Mapped[str] = mapped_column(
        String(20), default=CallDirection.INBOUND, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=CallStatus.ACTIVE, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(20))
    caller_number: Mapped[str | None] = mapped_column(String(20))
    callee_number: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recording_url: Mapped[str | None] = mapped_column(String(1024))
    transcript: Mapped[list] = mapped_column(JSONB, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[dict] = mapped_column(JSONB, default=dict)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)

    events: Mapped[list["CallEvent"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


class CallEvent(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "call_event"

    call_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("call.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # user|agent|tool|error
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    stt_ms: Mapped[int | None] = mapped_column(Integer)
    llm_ms: Mapped[int | None] = mapped_column(Integer)
    tts_ms: Mapped[int | None] = mapped_column(Integer)

    call: Mapped["Call"] = relationship(back_populates="events")
