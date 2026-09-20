"""Knowledge base: documents and their embedded chunks (pgvector)."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ofd.core.config import settings
from ofd.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from ofd.models.enums import DocStatus


class KnowledgeDoc(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "knowledge_doc"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(1024))  # storage path or URL
    status: Mapped[str] = mapped_column(String(20), default=DocStatus.PENDING, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    chunks: Mapped[list["DocChunk"]] = relationship(
        back_populates="doc", cascade="all, delete-orphan"
    )


class DocChunk(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "doc_chunk"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_doc.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBEDDINGS_DIM))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    doc: Mapped["KnowledgeDoc"] = relationship(back_populates="chunks")
