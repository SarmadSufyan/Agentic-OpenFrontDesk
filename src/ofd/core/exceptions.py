"""Typed application exceptions, mapped to HTTP problem responses in the API layer."""

from __future__ import annotations


class OFDError(Exception):
    """Base class for all OpenFrontDesk domain errors."""

    code: str = "error"
    http_status: int = 400

    def __init__(self, message: str | None = None, *, details: dict | None = None):
        self.message = message or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFound(OFDError):
    code = "not_found"
    http_status = 404


class Forbidden(OFDError):
    code = "forbidden"
    http_status = 403


class Unauthorized(OFDError):
    code = "unauthorized"
    http_status = 401


class Conflict(OFDError):
    code = "conflict"
    http_status = 409


class ValidationError(OFDError):
    code = "validation_error"
    http_status = 422


class TenantMismatch(Forbidden):
    """A resource was accessed outside its owning tenant."""

    code = "tenant_mismatch"


class TooManyRequests(OFDError):
    """Rate limit / quota exceeded."""

    code = "rate_limited"
    http_status = 429


class ProviderError(OFDError):
    """An external provider (STT/LLM/TTS/telephony) failed."""

    code = "provider_error"
    http_status = 502


class ConfigError(OFDError):
    code = "config_error"
    http_status = 500
