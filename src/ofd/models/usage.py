"""Usage events — per-provider units + cost, for analytics and billing."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class UsageEvent(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "usage_event"

    call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("call.id", ondelete="SET NULL"), index=True
    )
    provider_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # ProviderKind
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    units: Mapped[dict] = mapped_column(JSONB, default=dict)  # {minutes|tokens|chars: n}
    cost_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
