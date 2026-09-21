"""Audit log — a record of sensitive/config-changing actions per tenant."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. "tenant.update"
    target: Mapped[str | None] = mapped_column(String(200))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
