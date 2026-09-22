"""Platform admin endpoints: manage the voice priority allowlist and inspect live sessions.

Restricted to emails in ADMIN_EMAILS. This is how you "personally add someone by email" so they skip
the voice queue.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import get_db, require_admin
from ofd.models.user import User
from ofd.services import access as access_svc

router = APIRouter(prefix="/admin", tags=["admin"])


class AllowlistIn(BaseModel):
    email: str
    note: str | None = None


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
