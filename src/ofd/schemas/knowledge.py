"""Knowledge API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TextIn(BaseModel):
    title: str
    text: str


class UrlIn(BaseModel):
    title: str | None = None
    url: str


class KnowledgeDocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source_type: str
    status: str
    char_count: int
    chunk_count: int
    error: str | None = None
    created_at: datetime


class SearchHit(BaseModel):
    text: str
    score: float
    source_title: str | None = None
