"""Structured logging via structlog.

JSON in production (``LOG_JSON=true``), human-friendly in dev. Call ``configure_logging()``
once at startup, then ``get_logger(__name__)`` anywhere.
"""

from __future__ import annotations

import logging
import re
import sys

import structlog

from ofd.core.config import settings

_configured = False

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\-\s().]{8,}\d")


def _redact(value: str) -> str:
    """Redact emails and phone-number-shaped digit runs (10–15 digits) from a string."""
    value = _EMAIL.sub("[redacted-email]", value)

    def _phone_sub(m: re.Match) -> str:
        digits = sum(c.isdigit() for c in m.group())
        return "[redacted-phone]" if 10 <= digits <= 15 else m.group()

    return _PHONE.sub(_phone_sub, value)


def redact_pii(logger, method_name, event_dict):
    """structlog processor: scrub PII from string values in the log record."""
    for key, val in list(event_dict.items()):
        if isinstance(val, str):
            event_dict[key] = _redact(val)
    return event_dict


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        redact_pii,
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.LOG_JSON
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)
