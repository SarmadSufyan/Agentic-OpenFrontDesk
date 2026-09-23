"""Contact / custom-solution request schemas (public form + admin inbox)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Deliberately strict charset (no quotes, brackets or spaces): addresses end up in admin UI and
# email headers, so anything outside the common form is rejected rather than escaped later.
_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def normalize_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v):
        raise ValueError("Enter a valid email address")
    return v


NEEDS: dict[str, str] = {
    "whatsapp": "WhatsApp assistant",
    "chatbot": "Website chatbot",
    "voice": "Phone / voice receptionist",
    "hr_assistant": "HR and internal helpdesk assistant",
    "automation": "Workflow automation (n8n, Zapier, Make)",
    "crm": "CRM or calendar integration",
    "other": "Something else",
}
TEAM_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
BUDGETS = ["under_1k", "1k_5k", "5k_20k", "20k_plus", "not_sure"]
STATUSES = ["new", "contacted", "scheduled", "won", "lost", "spam"]


class ContactIn(BaseModel):
    # Strip before length checks, so a whitespace-only name or message is rejected.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., max_length=320)
    company: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=40)
    website: str | None = Field(None, max_length=300)
    team_size: str | None = None
    needs: list[str] = Field(default_factory=list, max_length=len(NEEDS))
    budget: str | None = None
    message: str = Field(..., min_length=10, max_length=5000)
    source: str | None = Field(None, max_length=40)
    # Honeypot: hidden in the form, so humans leave it empty and naive bots fill it in.
    company_fax: str | None = Field(None, max_length=200)

    @field_validator("name", "company", "phone", "website")
    @classmethod
    def _single_line(cls, v: str | None) -> str | None:
        # These go into email subjects and headers: collapse newlines/tabs to single spaces.
        return " ".join(v.split()) if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("needs")
    @classmethod
    def _needs(cls, v: list[str]) -> list[str]:
        unknown = [n for n in v if n not in NEEDS]
        if unknown:
            raise ValueError(f"Unknown need(s): {', '.join(unknown)}")
        return sorted(set(v))

    @field_validator("team_size")
    @classmethod
    def _team(cls, v: str | None) -> str | None:
        if v and v not in TEAM_SIZES:
            raise ValueError("Unknown team size")
        return v or None

    @field_validator("budget")
    @classmethod
    def _budget(cls, v: str | None) -> str | None:
        if v and v not in BUDGETS:
            raise ValueError("Unknown budget range")
        return v or None


class ContactAccepted(BaseModel):
    id: uuid.UUID | None = None
    status: str = "received"
    scheduling_url: str | None = None
    message: str = "Thanks, we have your request and will reply within one business day."


class ContactOptions(BaseModel):
    needs: dict[str, str]
    team_sizes: list[str]
    budgets: list[str]
    scheduling_enabled: bool


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    company: str | None = None
    phone: str | None = None
    website: str | None = None
    team_size: str | None = None
    needs: list[str] = []
    budget: str | None = None
    message: str
    status: str
    notes: str | None = None
    meeting_at: datetime | None = None
    meeting_link: str | None = None
    handled_by: str | None = None
    last_contacted_at: datetime | None = None
    user_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    source: str | None = None
    created_at: datetime


class ContactPage(BaseModel):
    items: list[ContactOut]
    total: int
    counts: dict[str, int]


class ContactUpdate(BaseModel):
    status: str | None = None
    notes: str | None = Field(None, max_length=10000)
    meeting_at: datetime | None = None
    meeting_link: str | None = Field(None, max_length=500)

    @field_validator("status")
    @classmethod
    def _status(cls, v: str | None) -> str | None:
        if v is not None and v not in STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(STATUSES)}")
        return v


class SchedulingEmailIn(BaseModel):
    message: str | None = Field(None, max_length=5000)
    link: str | None = Field(None, max_length=500)  # overrides SCHEDULING_URL for this email
