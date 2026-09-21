"""Workspace endpoints: the current tenant's profile and its agent config."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import AuthContext, get_context, get_db, require_roles
from ofd.core.exceptions import NotFound
from ofd.schemas.workspace import AgentOut, AgentUpdate, TenantOut, TenantUpdate
from ofd.services import audit as audit_svc
from ofd.services import tenants as tenants_svc

router = APIRouter(tags=["workspace"])


@router.get("/tenants/current", response_model=TenantOut)
async def get_tenant(ctx: AuthContext = Depends(get_context)):
    return ctx.tenant


@router.patch("/tenants/current", response_model=TenantOut)
async def update_tenant(
    body: TenantUpdate,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await tenants_svc.update_tenant(db, ctx.tenant, body.model_dump(exclude_unset=True))
    await audit_svc.record(
        db, tenant_id=ctx.tenant.id, actor_user_id=ctx.user.id, action="tenant.update"
    )
    return result


@router.get("/agents/current", response_model=AgentOut)
async def get_agent(ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)):
    agent = await tenants_svc.get_default_agent(db, ctx.tenant.id)
    if not agent:
        raise NotFound("No agent configured for this workspace")
    return agent


@router.put("/agents/current", response_model=AgentOut)
async def update_agent(
    body: AgentUpdate,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    agent = await tenants_svc.get_default_agent(db, ctx.tenant.id)
    if not agent:
        raise NotFound("No agent configured for this workspace")
    result = await tenants_svc.update_agent(db, agent, body.model_dump(exclude_unset=True))
    await audit_svc.record(
        db, tenant_id=ctx.tenant.id, actor_user_id=ctx.user.id, action="agent.update"
    )
    return result
