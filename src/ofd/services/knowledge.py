"""Knowledge service: ingest documents into pgvector, reindex, delete, and search."""

from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import NotFound
from ofd.core.logging import get_logger
from ofd.models.enums import DocStatus
from ofd.models.knowledge import DocChunk, KnowledgeDoc
from ofd.providers.registry import get_embeddings
from ofd.rag.chunk import chunk_text
from ofd.rag.parse import extract_text
from ofd.rag.retrieve import RetrievedChunk
from ofd.rag.retrieve import search as _search

logger = get_logger("ofd.services.knowledge")


async def create_and_ingest(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    title: str,
    source_type: str,
    data: bytes | None = None,
    text: str | None = None,
    url: str | None = None,
) -> KnowledgeDoc:
    doc = KnowledgeDoc(
        tenant_id=tenant_id,
        title=title,
        source_type=source_type,
        source_ref=url,
        status=DocStatus.PROCESSING,
    )
    db.add(doc)
    await db.flush()

    try:
        raw = await extract_text(source_type, data=data, text=text, url=url)
        chunks = chunk_text(
            raw,
            target_tokens=settings.RAG_CHUNK_TARGET_TOKENS,
            overlap_tokens=settings.RAG_CHUNK_OVERLAP_TOKENS,
        )
        if not chunks:
            raise ValueError("No text extracted from source")

        vectors = await get_embeddings().embed(chunks)
        for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                DocChunk(
                    tenant_id=tenant_id,
                    doc_id=doc.id,
                    chunk_index=i,
                    text=chunk,
                    embedding=vec,
                    meta={"source_title": title},
                )
            )
        doc.char_count = len(raw)
        doc.chunk_count = len(chunks)
        doc.status = DocStatus.READY
        await db.flush()
        logger.info("ingested", doc_id=str(doc.id), chunks=len(chunks), chars=len(raw))
    except Exception as exc:
        doc.status = DocStatus.FAILED
        doc.error = str(exc)[:500]
        await db.flush()
        logger.warning("ingest_failed", doc_id=str(doc.id), error=str(exc))
        raise
    return doc


async def reindex(db: AsyncSession, *, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> KnowledgeDoc:
    """Re-embed existing chunk texts (e.g. after changing the embeddings model)."""
    doc = await db.get(KnowledgeDoc, doc_id)
    if not doc or doc.tenant_id != tenant_id:
        raise NotFound("Knowledge doc not found")
    chunks = (
        (await db.execute(select(DocChunk).where(DocChunk.doc_id == doc_id).order_by(DocChunk.chunk_index)))
        .scalars()
        .all()
    )
    if chunks:
        vectors = await get_embeddings().embed([c.text for c in chunks])
        for c, vec in zip(chunks, vectors, strict=True):
            c.embedding = vec
    doc.status = DocStatus.READY
    await db.flush()
    return doc


async def delete_doc(db: AsyncSession, *, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> None:
    doc = await db.get(KnowledgeDoc, doc_id)
    if not doc or doc.tenant_id != tenant_id:
        raise NotFound("Knowledge doc not found")
    await db.execute(sa_delete(KnowledgeDoc).where(KnowledgeDoc.id == doc_id))
    await db.flush()


async def list_docs(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[KnowledgeDoc]:
    stmt = select(KnowledgeDoc).where(KnowledgeDoc.tenant_id == tenant_id).order_by(
        KnowledgeDoc.created_at.desc()
    )
    return list((await db.execute(stmt)).scalars().all())


async def search(
    db: AsyncSession, *, tenant_id: uuid.UUID, query: str, k: int | None = None
) -> list[RetrievedChunk]:
    return await _search(db, tenant_id=tenant_id, query=query, k=k)
