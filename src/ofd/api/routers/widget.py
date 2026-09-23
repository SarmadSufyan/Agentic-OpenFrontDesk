"""Public embeddable chat widget: serves widget.js and a grounded per-agent text-chat endpoint.

No auth (it's meant to run on public sites); resolved by the tenant slug. Text chat is cheap, so it is
not concurrency-gated, only rate-limited per tenant. CORS is open so the widget works cross-origin.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import get_db
from ofd.api.widgetjs import WIDGET_DEMO_HTML, WIDGET_JS
from ofd.core.config import settings
from ofd.core.exceptions import NotFound, TooManyRequests
from ofd.services import chat as chat_svc
from ofd.services import quota as quota_svc
from ofd.services import tenants as tenants_svc

router = APIRouter(tags=["widget"])


class ChatIn(BaseModel):
    message: str
    history: list[dict] | None = None
    session_id: str | None = None


class ChatOut(BaseModel):
    reply: str
    sources: list[str] = []
    session_id: str | None = None


@router.get("/widget.js")
async def widget_js() -> Response:
    return Response(content=WIDGET_JS, media_type="application/javascript")


@router.get("/widget-demo", response_class=HTMLResponse)
async def widget_demo() -> str:
    return WIDGET_DEMO_HTML


@router.get("/widget/{slug}/config")
async def widget_config(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    tenant = await tenants_svc.get_tenant_by_slug(db, slug)
    if not tenant:
        raise NotFound("Unknown widget")
    agent = await tenants_svc.get_default_agent(db, tenant.id)
    return {"name": tenant.name, "greeting": agent.greeting if agent else "Hi! How can I help?"}


@router.post("/widget/{slug}/chat", response_model=ChatOut)
async def widget_chat(slug: str, body: ChatIn, db: AsyncSession = Depends(get_db)) -> ChatOut:
    tenant = await tenants_svc.get_tenant_by_slug(db, slug)
    if not tenant:
        raise NotFound("Unknown widget")
    if settings.RATE_LIMIT_ENABLED:
        ok, _ = await quota_svc.check_rate(tenant.id, "widget_chat", 60, 60)
        if not ok:
            raise TooManyRequests("Too many messages, please slow down.")
    agent = await tenants_svc.get_default_agent(db, tenant.id)
    res = await chat_svc.chat(
        db, tenant=tenant, agent=agent, message=body.message, history=body.history
    )
    return ChatOut(reply=res["reply"], sources=res["sources"], session_id=body.session_id)
