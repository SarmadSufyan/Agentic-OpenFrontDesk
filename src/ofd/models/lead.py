"""Lead / message captured during a call."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Lead(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "lead"

    call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("call.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(320))
    intent: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
