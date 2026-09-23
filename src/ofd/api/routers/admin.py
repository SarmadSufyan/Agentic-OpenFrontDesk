"""Platform admin endpoints: the custom-solution inbox, the voice priority allowlist, and live
voice sessions.

Restricted to emails in ADMIN_EMAILS. The allowlist is how you "personally add someone by email" so
they skip the voice queue.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import get_db, require_admin
from ofd.models.user import User
from ofd.schemas.contact import (
    STATUSES,
    ContactOut,
    ContactPage,
    ContactUpdate,
    SchedulingEmailIn,
    normalize_email,
)
from ofd.services import access as access_svc
from ofd.services import contact as contact_svc

router = APIRouter(prefix="/admin", tags=["admin"])


class AllowlistIn(BaseModel):
    email: str
    note: str | None = Field(None, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)


@router.get("/allowlist")
async def list_allowlist(
    _admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    entries = await access_svc.list_allowlist(db)
    return [{"email": e.email, "note": e.note, "created_at": e.created_at} for e in entries]


@router.post("/allowlist", status_code=201)
async def add_allowlist(
    body: AllowlistIn, _admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> dict:
    e = await access_svc.add_allowlist(db, email=body.email, note=body.note)
    return {"email": e.email, "note": e.note}


@router.delete("/allowlist/{email}", status_code=204)
async def remove_allowlist(
    email: str, _admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> None:
    await access_svc.remove_allowlist(db, email=email)


@router.get("/voice/sessions")
async def voice_sessions(_admin: User = Depends(require_admin)) -> dict:
    return await access_svc.admin_snapshot()


# --------------------------------------------------------------------------- contact inbox
@router.get("/contact-requests", response_model=ContactPage)
async def list_contact_requests(
    status: str | None = Query(None, description=f"One of: {', '.join(STATUSES)}"),
    q: str | None = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ContactPage:
    items, total, counts = await contact_svc.list_requests(
        db, status=status, q=q, limit=limit, offset=offset
    )
    return ContactPage(
        items=[ContactOut.model_validate(i) for i in items], total=total, counts=counts
    )


@router.get("/contact-requests/{req_id}", response_model=ContactOut)
async def get_contact_request(
    req_id: uuid.UUID, _admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    return await contact_svc.get_request(db, req_id)


@router.patch("/contact-requests/{req_id}", response_model=ContactOut)
async def update_contact_request(
    req_id: uuid.UUID,
    body: ContactUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await contact_svc.update_request(
        db, req_id, body.model_dump(exclude_unset=True), admin_email=admin.email
    )


@router.post("/contact-requests/{req_id}/scheduling-email", response_model=ContactOut)
async def send_scheduling_email(
    req_id: uuid.UUID,
    body: SchedulingEmailIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Email the requester a personal note with the (prefilled) booking link."""
    return await contact_svc.send_scheduling_email(
        db, req_id, admin_email=admin.email, message=body.message, link=body.link
    )


@router.delete("/contact-requests/{req_id}", status_code=204)
async def delete_contact_request(
    req_id: uuid.UUID, _admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> None:
    """Permanently remove a request (spam, or a data-deletion request from the person)."""
    await contact_svc.delete_request(db, req_id)
