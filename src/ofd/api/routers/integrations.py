"""Integrations management (dashboard): outbound webhooks and API keys.

Owner/admin only. Secrets and keys are shown exactly once (on create or rotation); list views only
carry a hint, so an XSS or a shoulder-surfer on the dashboard cannot read them back later.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import AuthContext, get_db, require_roles
from ofd.schemas.automation import (
    ApiKeyCreated,
    ApiKeyIn,
    ApiKeyOut,
    DeliveryOut,
    EventTypeOut,
    WebhookIn,
    WebhookOut,
    WebhookUpdate,
    WebhookWithSecret,
)
from ofd.services import apikeys as apikeys_svc
from ofd.services import audit as audit_svc
from ofd.services import webhooks as webhooks_svc

router = APIRouter(prefix="/integrations", tags=["integrations"])
managers = require_roles("owner", "admin")


def _with_secret(ep) -> WebhookWithSecret:
    return WebhookWithSecret(**WebhookOut.of(ep).model_dump(), secret=ep.secret)


@router.get("/events", response_model=list[EventTypeOut])
async def event_types() -> list[EventTypeOut]:
    return [EventTypeOut(type=k, description=v) for k, v in webhooks_svc.EVENT_TYPES.items()]


# --------------------------------------------------------------------------- webhooks
@router.get("/webhooks", response_model=list[WebhookOut])
async def list_webhooks(ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)):
    eps = await webhooks_svc.list_endpoints(db, tenant_id=ctx.tenant.id)
    return [WebhookOut.of(ep) for ep in eps]


@router.post("/webhooks", response_model=WebhookWithSecret, status_code=201)
async def create_webhook(
    body: WebhookIn, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    ep = await webhooks_svc.create_endpoint(
        db, tenant_id=ctx.tenant.id, url=body.url, events=body.events, description=body.description
    )
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="webhook.create",
        target=ep.url,
    )
    return _with_secret(ep)


@router.patch("/webhooks/{endpoint_id}", response_model=WebhookOut)
async def update_webhook(
    endpoint_id: uuid.UUID,
    body: WebhookUpdate,
    ctx: AuthContext = Depends(managers),
    db: AsyncSession = Depends(get_db),
):
    ep = await webhooks_svc.update_endpoint(
        db,
        tenant_id=ctx.tenant.id,
        endpoint_id=endpoint_id,
        data=body.model_dump(exclude_unset=True),
    )
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="webhook.update",
        target=ep.url,
    )
    return WebhookOut.of(ep)


@router.delete("/webhooks/{endpoint_id}", status_code=204)
async def delete_webhook(
    endpoint_id: uuid.UUID, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
) -> None:
    await webhooks_svc.delete_endpoint(db, tenant_id=ctx.tenant.id, endpoint_id=endpoint_id)
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="webhook.delete",
        target=str(endpoint_id),
    )


@router.post("/webhooks/{endpoint_id}/rotate-secret", response_model=WebhookWithSecret)
async def rotate_webhook_secret(
    endpoint_id: uuid.UUID, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    ep = await webhooks_svc.rotate_secret(db, tenant_id=ctx.tenant.id, endpoint_id=endpoint_id)
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="webhook.rotate",
        target=ep.url,
    )
    return _with_secret(ep)


@router.post("/webhooks/{endpoint_id}/test", response_model=DeliveryOut)
async def test_webhook(
    endpoint_id: uuid.UUID, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    """Send a signed `webhook.test` event now and return the delivery result."""
    ep = await webhooks_svc.get_endpoint(db, tenant_id=ctx.tenant.id, endpoint_id=endpoint_id)
    return await webhooks_svc.send_test(db, ep)


@router.get("/webhooks/{endpoint_id}/deliveries", response_model=list[DeliveryOut])
async def list_deliveries(
    endpoint_id: uuid.UUID, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    return await webhooks_svc.list_deliveries(db, tenant_id=ctx.tenant.id, endpoint_id=endpoint_id)


# --------------------------------------------------------------------------- API keys
@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)):
    return await apikeys_svc.list_keys(db, tenant_id=ctx.tenant.id)


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    body: ApiKeyIn, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    key, raw = await apikeys_svc.create_key(
        db, tenant_id=ctx.tenant.id, name=body.name, created_by=ctx.user.id
    )
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="apikey.create",
        target=key.name,
    )
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=raw)


@router.delete("/api-keys/{key_id}", response_model=ApiKeyOut)
async def revoke_api_key(
    key_id: uuid.UUID, ctx: AuthContext = Depends(managers), db: AsyncSession = Depends(get_db)
):
    key = await apikeys_svc.revoke_key(db, tenant_id=ctx.tenant.id, key_id=key_id)
    await audit_svc.record(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        action="apikey.revoke",
        target=key.name,
    )
    return key
