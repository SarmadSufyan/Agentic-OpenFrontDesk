"""Retrieval: embed the query, cosine-search pgvector, return grounded chunks with sources."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.models.knowledge import DocChunk, KnowledgeDoc
from ofd.providers.registry import get_embeddings


@dataclass
class RetrievedChunk:
    text: str
    score: float  # similarity (1 - cosine_distance)
    doc_id: uuid.UUID
    chunk_index: int
    source_title: str | None = None


async def search(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    k: int | None = None,
) -> list[RetrievedChunk]:
    k = k or settings.RAG_TOP_K
    embedder = get_embeddings()
    query_vec = (await embedder.embed([query]))[0]

    distance = DocChunk.embedding.cosine_distance(query_vec)
    stmt = (
        select(DocChunk, distance.label("distance"), KnowledgeDoc.title)
        .join(KnowledgeDoc, KnowledgeDoc.id == DocChunk.doc_id)
        .where(DocChunk.tenant_id == tenant_id)
        .order_by(distance)
        .limit(k)
    )
    rows = (await db.execute(stmt)).all()
    return [
        RetrievedChunk(
            text=chunk.text,
            score=round(1.0 - float(dist), 4),
            doc_id=chunk.doc_id,
            chunk_index=chunk.chunk_index,
            source_title=title,
        )
        for chunk, dist, title in rows
    ]


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as grounded context for the LLM (sources tracked separately)."""
    if not chunks:
        return "NO_RESULTS"
    parts = []
    for i, c in enumerate(chunks, 1):
        src = f" (source: {c.source_title})" if c.source_title else ""
        parts.append(f"[{i}]{src}\n{c.text}")
    return "\n\n".join(parts)
