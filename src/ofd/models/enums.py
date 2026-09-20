"""Enum value constants used across models (stored as strings for migration simplicity)."""

from __future__ import annotations

import enum


class Role(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class DocStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class SourceType(enum.StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    TEXT = "text"
    URL = "url"


class CallDirection(enum.StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    TEST = "test"


class CallStatus(enum.StrEnum):
    RINGING = "ringing"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class CallOutcome(enum.StrEnum):
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    MESSAGE_TAKEN = "message_taken"
    TRANSFERRED = "transferred"
    ANSWERED = "answered"
    ABANDONED = "abandoned"
    FAILED = "failed"


class BookingStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


class IntegrationType(enum.StrEnum):
    CALCOM = "calcom"
    GOOGLE_CALENDAR = "google_calendar"
    TWILIO = "twilio"
    TELNYX = "telnyx"
    CRM_WEBHOOK = "crm_webhook"
    SLACK = "slack"


class ProviderKind(enum.StrEnum):
    STT = "stt"
    LLM = "llm"
    TTS = "tts"
    EMBEDDINGS = "embeddings"
