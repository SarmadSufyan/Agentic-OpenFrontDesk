"""Custom-solution requests from the contact form (platform-level, handled by the admins)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TimestampMixin, UUIDMixin


class ContactRequest(Base, UUIDMixin, TimestampMixin):
    """A company asking for a tailored setup (WhatsApp, HR assistant, automations, ...).

    Not tenant-scoped: prospects usually have no workspace yet. When a signed-in user submits the
    form, their user and workspace are linked so the admin sees the context.
    """

    __tablename__ = "contact_request"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(300))
    team_size: Mapped[str | None] = mapped_column(String(20))
    needs: Mapped[list] = mapped_column(JSONB, default=list)  # e.g. ["whatsapp", "hr_assistant"]
    budget: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="new", index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)  # internal, admin-only
    meeting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    handled_by: Mapped[str | None] = mapped_column(String(320))  # admin email of the last change
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="SET NULL")
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenant.id", ondelete="SET NULL")
    )
    source: Mapped[str | None] = mapped_column(String(40))  # contact_page, dashboard, api
    ip_hash: Mapped[str | None] = mapped_column(String(64))  # salted hash, never the raw IP
    user_agent: Mapped[str | None] = mapped_column(String(300))
