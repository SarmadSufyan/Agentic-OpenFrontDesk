"""Tenant (workspace) and agent config schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    vertical: str | None = None
    timezone: str
    business_hours: dict = {}
    address: dict = {}
    plan: str
    created_at: datetime


class TenantUpdate(BaseModel):
    name: str | None = None
    vertical: str | None = None
    timezone: str | None = None
    business_hours: dict | None = None
    address: dict | None = None
    settings: dict | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    voice: str
    greeting: str
    tone: str
    persona: dict = {}
    escalation_rules: dict = {}
    booking_rules: dict = {}
    is_active: bool


class AgentUpdate(BaseModel):
    name: str | None = None
    voice: str | None = None
    greeting: str | None = None
    tone: str | None = None
    persona: dict | None = None
    escalation_rules: dict | None = None
    booking_rules: dict | None = None
    is_active: bool | None = None
