"""Knowledge service: ingest documents into pgvector, reindex, delete, and search.

Ingestion is split so the API can create the doc (status=pending) and return immediately, then run
the heavy parse/chunk/embed work in the background (`ingest_job`). `create_and_ingest` keeps the
synchronous path for scripts/seeding.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import NotFound
from ofd.core.logging import get_logger
from ofd.db.session import session_scope
from ofd.models.enums import DocStatus
from ofd.models.knowledge import DocChunk, KnowledgeDoc
from ofd.providers.registry import get_embeddings
from ofd.rag.chunk import chunk_text
from ofd.rag.parse import extract_text
from ofd.rag.retrieve import RetrievedChunk
from ofd.rag.retrieve import search as _search

logger = get_logger("ofd.services.knowledge")


async def create_doc(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    title: str,
    source_type: str,
    source_ref: str | None = None,
) -> KnowledgeDoc:
    doc = KnowledgeDoc(
        tenant_id=tenant_id,
        title=title,
        source_type=source_type,
        source_ref=source_ref,
        status=DocStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    return doc


async def run_ingestion(
    db: AsyncSession,
    *,
    doc: KnowledgeDoc,
    data: bytes | None = None,
    text: str | None = None,
    url: str | None = None,
) -> KnowledgeDoc:
    """Parse -> chunk -> embed -> store, on an existing doc. Sets status ready/failed."""
    doc.status = DocStatus.PROCESSING
    await db.flush()
    try:
        raw = await extract_text(doc.source_type, data=data, text=text, url=url)
        chunks = chunk_text(
            raw,
            target_tokens=settings.RAG_CHUNK_TARGET_TOKENS,
            overlap_tokens=settings.RAG_CHUNK_OVERLAP_TOKENS,
        )
        if not chunks:
            raise ValueError("No text extracted from source")

        await db.execute(sa_delete(DocChunk).where(DocChunk.doc_id == doc.id))  # replace on re-ingest
        vectors = await get_embeddings().embed(chunks)
        for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                DocChunk(
                    tenant_id=doc.tenant_id,
                    doc_id=doc.id,
                    chunk_index=i,
                    text=chunk,
                    embedding=vec,
                    meta={"source_title": doc.title},
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
    """Synchronous create + ingest (used by scripts/seeding)."""
    doc = await create_doc(
        db, tenant_id=tenant_id, title=title, source_type=source_type, source_ref=url
    )
    await run_ingestion(db, doc=doc, data=data, text=text, url=url)
    return doc


async def ingest_job(
    *,
    doc_id: uuid.UUID,
    data: bytes | None = None,
    text: str | None = None,
    url: str | None = None,
) -> None:
    """Background task: ingest an already-created doc in its own DB session."""
    async with session_scope() as db:
        doc = await db.get(KnowledgeDoc, doc_id)
        if doc is None:
            logger.warning("ingest_job_missing_doc", doc_id=str(doc_id))
            return
        try:
            await run_ingestion(db, doc=doc, data=data, text=text, url=url)
        except Exception:
            pass  # status already marked failed inside run_ingestion


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
