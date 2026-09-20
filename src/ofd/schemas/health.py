"""Health check response schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok", "degraded"])
    version: str
    env: str
    checks: dict[str, str] = {}
