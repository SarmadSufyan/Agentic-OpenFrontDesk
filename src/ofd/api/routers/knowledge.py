"""Knowledge base management API (ingest / list / reindex / delete / search).

Ingestion is synchronous here (fine for typical docs); Phase 4 can move it to a background job.
Tenant is resolved via the auth token, or `?tenant=<slug>` (default demo) in dev — see api/deps.py.
Write endpoints are per-tenant rate limited.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import get_active_tenant_id, get_db, rate_limit
from ofd.db.session import session_scope
from ofd.models.enums import SourceType
from ofd.schemas.knowledge import KnowledgeDocOut, SearchHit, TextIn, UrlIn
from ofd.services import audit as audit_svc
from ofd.services import knowledge as knowledge_svc

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# reads: plain tenant resolution; writes: same + a per-tenant rate limit
read_tenant = get_active_tenant_id
write_tenant = rate_limit("knowledge_write")


@router.get("", response_model=list[KnowledgeDocOut])
async def list_docs(
    tenant_id: uuid.UUID = Depends(read_tenant),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await knowledge_svc.list_docs(db, tenant_id=tenant_id)


# Create + commit the doc in its own session BEFORE scheduling the background task, so the task
# (which opens a fresh session) always sees a persisted row. Relying on the request session's
# deferred commit races the background task in FastAPI.
@router.post("/text", response_model=KnowledgeDocOut, status_code=202)
async def add_text(
    body: TextIn,
    background_tasks: BackgroundTasks,
    tenant_id: uuid.UUID = Depends(write_tenant),
):
    async with session_scope() as db:
        doc = await knowledge_svc.create_doc(
            db, tenant_id=tenant_id, title=body.title, source_type=SourceType.TEXT
        )
        await audit_svc.record(db, tenant_id=tenant_id, action="knowledge.add", target=body.title)
    background_tasks.add_task(knowledge_svc.ingest_job, doc_id=doc.id, text=body.text)
    return doc


@router.post("/url", response_model=KnowledgeDocOut, status_code=202)
async def add_url(
    body: UrlIn,
    background_tasks: BackgroundTasks,
    tenant_id: uuid.UUID = Depends(write_tenant),
):
    title = body.title or body.url
    async with session_scope() as db:
        doc = await knowledge_svc.create_doc(
            db, tenant_id=tenant_id, title=title, source_type=SourceType.URL, source_ref=body.url
        )
        await audit_svc.record(db, tenant_id=tenant_id, action="knowledge.add", target=body.url)
    background_tasks.add_task(knowledge_svc.ingest_job, doc_id=doc.id, url=body.url)
    return doc


@router.post("/file", response_model=KnowledgeDocOut, status_code=202)
async def add_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(write_tenant),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    source_type = {"pdf": SourceType.PDF, "docx": SourceType.DOCX}.get(ext, SourceType.TXT)
    data = await file.read()
    title = file.filename or "upload"
    async with session_scope() as db:
        doc = await knowledge_svc.create_doc(
            db, tenant_id=tenant_id, title=title, source_type=source_type
        )
        await audit_svc.record(db, tenant_id=tenant_id, action="knowledge.add", target=title)
    background_tasks.add_task(knowledge_svc.ingest_job, doc_id=doc.id, data=data)
    return doc


@router.post("/{doc_id}/reindex", response_model=KnowledgeDocOut)
async def reindex(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(write_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.reindex(db, tenant_id=tenant_id, doc_id=doc_id)


@router.delete("/{doc_id}", status_code=204)
async def delete_doc(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(write_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await knowledge_svc.delete_doc(db, tenant_id=tenant_id, doc_id=doc_id)
    await audit_svc.record(db, tenant_id=tenant_id, action="knowledge.delete", target=str(doc_id))


@router.get("/search", response_model=list[SearchHit])
async def search(
    q: str = Query(..., min_length=1),
    tenant_id: uuid.UUID = Depends(read_tenant),
    db: AsyncSession = Depends(get_db),
) -> list:
    hits = await knowledge_svc.search(db, tenant_id=tenant_id, query=q)
    return [SearchHit(text=h.text, score=h.score, source_title=h.source_title) for h in hits]
