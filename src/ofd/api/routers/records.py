"""Read endpoints for the dashboard: calls, bookings, leads, analytics."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import AuthContext, get_context, get_db, require_roles
from ofd.core.exceptions import NotFound
from ofd.schemas.records import (
    AnalyticsOut,
    AuditOut,
    BookingOut,
    CallDetailOut,
    CallOut,
    LeadOut,
)
from ofd.services import analytics as analytics_svc
from ofd.services import audit as audit_svc
from ofd.services import booking as booking_svc
from ofd.services import calls as calls_svc
from ofd.services import leads as leads_svc

router = APIRouter(tags=["records"])


@router.get("/calls", response_model=list[CallOut])
async def list_calls(ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)):
    return await calls_svc.list_calls(db, tenant_id=ctx.tenant.id)


@router.get("/calls/{call_id}", response_model=CallDetailOut)
async def get_call(
    call_id: uuid.UUID,
    ctx: AuthContext = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    call = await calls_svc.get_call(db, tenant_id=ctx.tenant.id, call_id=call_id)
    if not call:
        raise NotFound("Call not found")
    return call


@router.get("/bookings", response_model=list[BookingOut])
async def list_bookings(ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)):
    return await booking_svc.list_bookings(db, tenant_id=ctx.tenant.id)


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)):
    return await leads_svc.list_leads(db, tenant_id=ctx.tenant.id)


@router.get("/analytics/overview", response_model=AnalyticsOut)
async def analytics_overview(
    ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)
):
    return await analytics_svc.overview(db, tenant_id=ctx.tenant.id)


@router.get("/audit", response_model=list[AuditOut])
async def list_audit(
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    return await audit_svc.list_audit(db, tenant_id=ctx.tenant.id)
