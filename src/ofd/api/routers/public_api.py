"""Public REST API (/v1), authenticated by tenant API key.

This is what automation tools call: n8n HTTP Request nodes, Zapier / Make actions, or plain scripts.
Together with outbound webhooks it closes the loop: an event triggers a workflow, and the workflow
can act back on the workspace (ask the agent, log a lead from another channel, book a slot).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import ApiContext, get_api_context, get_db
from ofd.core.exceptions import NotFound
from ofd.schemas.automation import (
    ApiBookingIn,
    ApiChatIn,
    ApiChatOut,
    ApiLeadIn,
    MeOut,
    SlotOut,
)
from ofd.schemas.knowledge import SearchHit
from ofd.schemas.records import BookingOut, CallDetailOut, CallOut, LeadOut
from ofd.services import booking as booking_svc
from ofd.services import calls as calls_svc
from ofd.services import chat as chat_svc
from ofd.services import knowledge as knowledge_svc
from ofd.services import leads as leads_svc
from ofd.services import tenants as tenants_svc

router = APIRouter(prefix="/v1", tags=["public-api"])


@router.get("/me", response_model=MeOut)
async def me(api: ApiContext = Depends(get_api_context)) -> MeOut:
    """Verify a key and see which workspace it belongs to (used by n8n credential tests)."""
    return MeOut(
        workspace_id=api.tenant.id,
        workspace_name=api.tenant.name,
        workspace_slug=api.tenant.slug,
        key_name=api.key.name,
    )


@router.post("/chat", response_model=ApiChatOut)
async def chat(
    body: ApiChatIn, api: ApiContext = Depends(get_api_context), db: AsyncSession = Depends(get_db)
) -> ApiChatOut:
    """Ask the workspace's agent a question. Answers are grounded in its knowledge base, and the
    agent can capture leads or book appointments exactly as it does in the widget."""
    agent = await tenants_svc.get_default_agent(db, api.tenant.id)
    res = await chat_svc.chat(
        db, tenant=api.tenant, agent=agent, message=body.message, history=body.history
    )
    return ApiChatOut(reply=res["reply"], sources=res["sources"])


@router.get("/knowledge/search", response_model=list[SearchHit])
async def knowledge_search(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(5, ge=1, le=20),
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
) -> list[SearchHit]:
    hits = await knowledge_svc.search(db, tenant_id=api.tenant.id, query=q, k=k)
    return [SearchHit(text=h.text, score=h.score, source_title=h.source_title) for h in hits]


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    limit: int = Query(50, ge=1, le=200),
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    return await leads_svc.list_leads(db, tenant_id=api.tenant.id, limit=limit)


@router.post("/leads", response_model=LeadOut, status_code=201)
async def create_lead(
    body: ApiLeadIn, api: ApiContext = Depends(get_api_context), db: AsyncSession = Depends(get_db)
):
    """Log a lead from another channel (a web form, WhatsApp, email) so it sits in one inbox."""
    return await leads_svc.capture_lead(
        db,
        tenant_id=api.tenant.id,
        name=body.name,
        phone=body.phone,
        email=body.email,
        intent=body.intent,
        message=body.message,
        tags=[*body.tags, "api"],
    )


@router.get("/availability", response_model=list[SlotOut])
async def availability(
    date: datetime | None = Query(None, description="ISO date/time; omit for the next open slots"),
    limit: int = Query(5, ge=1, le=20),
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    slots = await booking_svc.check_availability(db, api.tenant, on_date=date, limit=limit)
    return [SlotOut(start=s.start, end=s.end) for s in slots]


@router.get("/bookings", response_model=list[BookingOut])
async def list_bookings(
    limit: int = Query(50, ge=1, le=200),
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    return await booking_svc.list_bookings(db, tenant_id=api.tenant.id, limit=limit)


@router.post("/bookings", response_model=BookingOut, status_code=201)
async def create_booking(
    body: ApiBookingIn,
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    return await booking_svc.book(
        db,
        api.tenant,
        name=body.name,
        phone=body.phone,
        service=body.service,
        start_at=body.start_at,
        slot_minutes=body.slot_minutes,
        notes=body.notes,
    )


@router.get("/calls", response_model=list[CallOut])
async def list_calls(
    limit: int = Query(50, ge=1, le=200),
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    return await calls_svc.list_calls(db, tenant_id=api.tenant.id, limit=limit)


@router.get("/calls/{call_id}", response_model=CallDetailOut)
async def get_call(
    call_id: uuid.UUID,
    api: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    call = await calls_svc.get_call(db, tenant_id=api.tenant.id, call_id=call_id)
    if not call:
        raise NotFound("Call not found")
    return call
