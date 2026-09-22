"""Platform-level access control: the priority allowlist (emails that skip the voice queue)."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ofd.db.base import Base, TimestampMixin, UUIDMixin


class AllowlistEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "access_allowlist"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
