"""Per-tenant integration config (calendar / SMS / CRM). Secrets encrypted at rest."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Integration(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "integration"

    type: Mapped[str] = mapped_column(String(40), nullable=False)  # IntegrationType
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # non-secret settings
    secret: Mapped[str | None] = mapped_column(Text)  # encrypted; never returned by the API
    status: Mapped[str] = mapped_column(String(20), default="connected", nullable=False)
