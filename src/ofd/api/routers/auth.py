"""Authentication endpoints: signup, login, refresh, me."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.api.deps import AuthContext, get_context, get_db
from ofd.core.exceptions import Unauthorized
from ofd.core.security import create_access_token, create_refresh_token, decode_token
from ofd.models.user import User
from ofd.schemas.auth import (
    LoginIn,
    MembershipOut,
    MeOut,
    RefreshIn,
    SignupIn,
    TokenOut,
    UserOut,
)
from ofd.services import auth as auth_svc

router = APIRouter(prefix="/auth", tags=["auth"])


async def _tokens_for(db: AsyncSession, user: User) -> TokenOut:
    tid = await auth_svc.first_tenant_id(db, user.id)
    role = await auth_svc.role_in_tenant(db, user_id=user.id, tenant_id=tid) if tid else None
    access = create_access_token(
        user_id=str(user.id), tenant_id=str(tid) if tid else None, role=role
    )
    refresh = create_refresh_token(user_id=str(user.id))
    return TokenOut(access_token=access, refresh_token=refresh, tenant_id=tid)


@router.post("/signup", response_model=TokenOut, status_code=201)
async def signup(body: SignupIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    user, _ = await auth_svc.signup(
        db,
        email=body.email,
        password=body.password,
        name=body.name,
        business_name=body.business_name,
    )
    return await _tokens_for(db, user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    user = await auth_svc.authenticate(db, email=body.email, password=body.password)
    return await _tokens_for(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise Unauthorized("Invalid refresh token")
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized("User not found or inactive")
    return await _tokens_for(db, user)


@router.get("/me", response_model=MeOut)
async def me(ctx: AuthContext = Depends(get_context), db: AsyncSession = Depends(get_db)) -> MeOut:
    memberships = await auth_svc.list_memberships(db, ctx.user.id)
    return MeOut(
        user=UserOut.model_validate(ctx.user),
        memberships=[
            MembershipOut(tenant_id=t.id, tenant_name=t.name, tenant_slug=t.slug, role=m.role)
            for m, t in memberships
        ],
    )
