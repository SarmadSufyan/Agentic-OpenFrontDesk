"""Public contact form for custom solutions (WhatsApp, HR assistant, automations, ...).

No login required; a signed-in user's account and workspace are attached when a token is present.
Abuse controls: a hidden honeypot field, a per-IP hourly limit, link-stuffing detection, and
de-duplication of double submits.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.contactpage import CONTACT_PAGE_HTML
from ofd.api.deps import bearer, get_db
from ofd.core.config import settings
from ofd.core.exceptions import TooManyRequests
from ofd.core.logging import get_logger
from ofd.core.security import decode_token
from ofd.schemas.contact import (
    BUDGETS,
    NEEDS,
    TEAM_SIZES,
    ContactAccepted,
    ContactIn,
    ContactOptions,
)
from ofd.services import contact as contact_svc
from ofd.services import quota as quota_svc

logger = get_logger("ofd.api.contact")
router = APIRouter(tags=["contact"])


def client_ip(request: Request) -> str | None:
    if settings.TRUST_PROXY_HEADERS:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _optional_identity(creds: HTTPAuthorizationCredentials | None) -> tuple[uuid.UUID | None, ...]:
    """(user_id, tenant_id) from a valid access token, else (None, None). Never raises."""
    if creds is None:
        return None, None
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            return None, None
        sub, tid = payload.get("sub"), payload.get("tid")
        return (uuid.UUID(sub) if sub else None), (uuid.UUID(tid) if tid else None)
    except Exception:
        return None, None


@router.get("/contact", response_class=HTMLResponse, include_in_schema=False)
async def contact_page() -> str:
    return CONTACT_PAGE_HTML


@router.get("/contact/options", response_model=ContactOptions)
async def contact_options() -> ContactOptions:
    """Choices for building the form (used by the web frontend)."""
    return ContactOptions(
        needs=NEEDS,
        team_sizes=TEAM_SIZES,
        budgets=BUDGETS,
        scheduling_enabled=bool(settings.SCHEDULING_URL),
    )


@router.post("/contact", response_model=ContactAccepted, status_code=202)
async def submit_contact(
    body: ContactIn,
    request: Request,
    background: BackgroundTasks,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> ContactAccepted:
    if body.company_fax:  # honeypot tripped: look successful, store nothing
        logger.info("contact_honeypot")
        return ContactAccepted()

    ip = client_ip(request)
    if ip and settings.RATE_LIMIT_ENABLED:
        allowed, _ = await quota_svc.hit(
            f"contact:{contact_svc.hash_ip(ip)}", settings.CONTACT_RATE_LIMIT_PER_HOUR, 3600
        )
        if not allowed:
            raise TooManyRequests("Too many requests from this network. Please try again later.")

    user_id, tenant_id = _optional_identity(creds)
    req, is_new = await contact_svc.create_request(
        db,
        body,
        user_id=user_id,
        tenant_id=tenant_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()  # persist before the notification task reads it
    if is_new:
        background.add_task(contact_svc.notify_new_request, req.id)

    spam = req.status == "spam"
    return ContactAccepted(
        id=None if spam else req.id,
        scheduling_url=None if spam else contact_svc.scheduling_link(req.name, req.email),
    )
