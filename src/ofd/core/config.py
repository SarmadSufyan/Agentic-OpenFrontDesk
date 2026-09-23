"""Typed application settings, loaded from environment / `.env`.

Single source of truth for configuration. Import the singleton:

    from ofd.core.config import settings

Provider selection keys (STT_PROVIDER, LLM_PROVIDER, ...) drive the registry in
`ofd.providers.registry`, so swapping free <-> premium is an env change, not code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    ENV: Literal["development", "production", "test"] = "development"
    APP_NAME: str = "OpenFrontDesk"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Auth ---
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 14

    # --- Database ---
    POSTGRES_USER: str = "ofd"
    POSTGRES_PASSWORD: str = "ofd"
    POSTGRES_DB: str = "openfrontdesk"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""  # if blank, assembled from POSTGRES_* below

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Storage ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_DIR: str = "./data/storage"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # --- Provider selection ---
    STT_PROVIDER: str = "groq"
    LLM_PROVIDER: str = "groq"
    TTS_PROVIDER: str = "kokoro"
    EMBEDDINGS_PROVIDER: str = "fastembed"

    # --- Groq ---
    GROQ_API_KEY: str = ""
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    GROQ_LLM_MODEL: str = "openai/gpt-oss-20b"

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDINGS_MODEL: str = "text-embedding-004"

    # --- Kokoro (self-hosted TTS) ---
    KOKORO_BASE_URL: str = "http://localhost:8880"
    KOKORO_VOICE: str = "af_heart"

    # --- Ollama (dev/offline LLM) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # --- Premium providers ---
    DEEPGRAM_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""
    CARTESIA_VOICE: str = ""
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    OPENAI_API_KEY: str = ""

    # --- Embeddings / RAG ---
    EMBEDDINGS_DIM: int = 384  # bge-small (fastembed default); must match vector column
    RAG_CHUNK_TARGET_TOKENS: int = 400
    RAG_CHUNK_OVERLAP_TOKENS: int = 60
    RAG_TOP_K: int = 5

    # --- Voice transport / telephony ---
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    TELEPHONY_PROVIDER: Literal["none", "telnyx", "twilio"] = "none"
    TELNYX_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""

    # --- Integrations ---
    CALENDAR_BACKEND: Literal["internal", "calcom"] = "internal"
    CALCOM_BASE_URL: str = "https://api.cal.com/v2"
    CALCOM_API_KEY: str = ""
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    SMS_PROVIDER: Literal["none", "twilio", "telnyx"] = "none"

    # --- Observability ---
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    # --- Security / limits ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MIN: int = 120
    SECURITY_HEADERS: bool = True
    RECORDING_ENABLED: bool = False

    # --- SaaS access control (free-tier fair use) ---
    MAX_CONCURRENT_VOICE: int = 3  # simultaneous live voice sessions before queueing
    VOICE_SESSION_TTL_SECONDS: int = 360  # a granted voice slot expires if not heartbeated
    ADMIN_EMAILS: str = ""  # comma-separated admin emails (platform admins)
    ACCESS_ALLOWLIST: str = ""  # comma-separated emails that skip the voice queue

    # --- Automations (outbound webhooks + public API) ---
    WEBHOOK_ALLOW_PRIVATE: bool = (
        False  # allow delivery to private/internal hosts (self-hosted n8n)
    )
    WEBHOOK_TIMEOUT_SECONDS: float = 10.0
    WEBHOOK_MAX_ATTEMPTS: int = 3
    WEBHOOK_DISABLE_AFTER_FAILURES: int = (
        25  # auto-disable an endpoint after N consecutive failures
    )
    API_RATE_LIMIT_PER_MIN: int = 120  # per-tenant limit for API-key requests

    # --- Contact / custom solutions ---
    PUBLIC_BASE_URL: str = "http://localhost:8000"  # used for links in emails
    SCHEDULING_URL: str = ""  # Cal.com / Calendly link offered after a contact request
    CONTACT_NOTIFY_EMAILS: str = ""  # who is emailed about new requests (defaults to ADMIN_EMAILS)
    CONTACT_WEBHOOK_URL: str = ""  # optional Slack / n8n / Zapier hook for new requests
    CONTACT_RATE_LIMIT_PER_HOUR: int = 5  # submissions per client IP
    TRUST_PROXY_HEADERS: bool = False  # read the client IP from X-Forwarded-For (behind nginx)

    # --- Email (SMTP) ---
    SMTP_HOST: str = ""  # empty = email disabled (requests are still stored and shown to admins)
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""  # e.g. "OpenFrontDesk <hello@yourdomain.com>"
    SMTP_STARTTLS: bool = True
    SMTP_SSL: bool = False  # implicit TLS (usually port 465)

    # ----------------------------------------------------------------- helpers
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (asyncpg)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    @property
    def access_allowlist(self) -> set[str]:
        return {e.strip().lower() for e in self.ACCESS_ALLOWLIST.split(",") if e.strip()}

    @property
    def contact_notify_emails(self) -> list[str]:
        raw = self.CONTACT_NOTIFY_EMAILS or self.ADMIN_EMAILS
        return sorted({e.strip().lower() for e in raw.split(",") if e.strip()})

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
