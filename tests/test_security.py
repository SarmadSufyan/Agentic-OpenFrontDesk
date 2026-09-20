"""Unit tests for PII log redaction and the metrics registry (pure — no DB/app)."""

from __future__ import annotations

from ofd.core import metrics
from ofd.core.logging import _redact


def test_redacts_email() -> None:
    assert "[redacted-email]" in _redact("email me at jane.doe@example.com please")


def test_redacts_phone() -> None:
    assert "[redacted-phone]" in _redact("call +1 555-123-4567 anytime")
    assert "[redacted-phone]" in _redact("number is 5551234567")


def test_keeps_dates_versions_ports() -> None:
    out = _redact("released 2026-09-21, version 0.1.0, on port 8080")
    assert "2026-09-21" in out
    assert "0.1.0" in out
    assert "8080" in out


def test_metrics_render() -> None:
    metrics.incr("http_requests_total", method="GET", status="200")
    out = metrics.render()
    assert "ofd_http_requests_total" in out
    assert "ofd_info" in out
    assert "ofd_uptime_seconds" in out
