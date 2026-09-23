"""Unit tests for automations: webhook signing, SSRF guard, delivery retries, commit-gated emit,
API key handling, and auth on the new endpoints. No database or network required."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ofd.api.app import app
from ofd.core.config import settings
from ofd.core.exceptions import ValidationError
from ofd.models.automation import WebhookEndpoint
from ofd.services import apikeys, webhooks

client = TestClient(app)


# --------------------------------------------------------------------------- signing
def test_signature_matches_documented_scheme() -> None:
    body = b'{"type":"lead.created"}'
    sig = webhooks.sign("whsec_test", 1700000000, body)
    expected = hmac.new(b"whsec_test", b"1700000000." + body, hashlib.sha256).hexdigest()
    assert sig == f"sha256={expected}"


def test_secret_format() -> None:
    s = webhooks.generate_secret()
    assert s.startswith("whsec_") and len(s) > 30


# --------------------------------------------------------------------------- SSRF guard
@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.1.2.3", "172.16.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0", "::1"],
)
def test_blocks_internal_addresses(ip: str) -> None:
    assert webhooks.is_blocked_ip(ip)


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"])
def test_allows_public_addresses(ip: str) -> None:
    assert not webhooks.is_blocked_ip(ip)


def test_blocks_ipv4_mapped_ipv6() -> None:
    assert webhooks.is_blocked_ip("::ffff:127.0.0.1")


@pytest.mark.parametrize(
    "url", ["ftp://example.com/x", "not a url", "http://", "file:///etc/passwd"]
)
def test_rejects_bad_url_syntax(url: str) -> None:
    with pytest.raises(ValidationError):
        webhooks.check_url_syntax(url)


async def test_rejects_private_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE", False)
    with pytest.raises(ValidationError):
        await webhooks.assert_deliverable("http://127.0.0.1:5678/webhook/x")


async def test_private_target_allowed_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE", True)
    await webhooks.assert_deliverable("http://127.0.0.1:5678/webhook/x")


def test_event_normalization() -> None:
    assert webhooks._normalize_events([]) == ["*"]
    assert webhooks._normalize_events(["lead.created", "*"]) == ["*"]
    assert webhooks._normalize_events(["lead.created", "lead.created"]) == ["lead.created"]
    with pytest.raises(ValidationError):
        webhooks._normalize_events(["lead.deleted"])


# --------------------------------------------------------------------------- delivery
class _FakeDB:
    def __init__(self) -> None:
        self.added: list = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def _endpoint() -> WebhookEndpoint:
    return WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        url="http://receiver.test/hook",
        events=["*"],
        secret="whsec_unit",
        is_active=True,
        failure_count=0,
    )


def _mock_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(webhooks.httpx, "AsyncClient", factory)


async def _no_sleep(_s: float) -> None:
    return None


async def test_delivery_retries_then_succeeds_with_valid_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE", True)
    monkeypatch.setattr(webhooks.asyncio, "sleep", _no_sleep)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(503 if len(seen) == 1 else 200)

    _mock_client(monkeypatch, handler)
    ep, db = _endpoint(), _FakeDB()
    delivery = await webhooks._deliver(db, ep, webhooks._envelope(ep.tenant_id, "lead.created", {}))

    assert delivery.success and delivery.attempts == 2 and delivery.status_code == 200
    assert ep.failure_count == 0
    req = seen[-1]
    ts = int(req.headers["X-OFD-Timestamp"])
    assert req.headers["X-OFD-Signature"] == webhooks.sign("whsec_unit", ts, req.content)
    assert json.loads(req.content)["type"] == "lead.created"


async def test_delivery_does_not_retry_client_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE", True)
    monkeypatch.setattr(webhooks.asyncio, "sleep", _no_sleep)
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    _mock_client(monkeypatch, handler)
    ep, db = _endpoint(), _FakeDB()
    delivery = await webhooks._deliver(db, ep, webhooks._envelope(ep.tenant_id, "lead.created", {}))
    assert not delivery.success and delivery.attempts == 1 and len(calls) == 1
    assert ep.failure_count == 1


async def test_endpoint_auto_disables_after_repeated_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_ALLOW_PRIVATE", True)
    monkeypatch.setattr(settings, "WEBHOOK_DISABLE_AFTER_FAILURES", 2)
    _mock_client(monkeypatch, lambda request: httpx.Response(410))
    ep, db = _endpoint(), _FakeDB()
    for _ in range(2):
        await webhooks._deliver(db, ep, webhooks._envelope(ep.tenant_id, "lead.created", {}))
    assert ep.is_active is False


# --------------------------------------------------------------------------- commit-gated emit
def test_events_emit_only_after_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple] = []
    monkeypatch.setattr(webhooks, "emit", lambda *a: emitted.append(a))
    tid = uuid.uuid4()

    # Services queue events after a flush, i.e. inside an open transaction; begin() mirrors that.
    s = Session()
    s.begin()
    s.info.setdefault(webhooks._PENDING_KEY, []).append((tid, "lead.created", {"id": "1"}))
    assert emitted == []
    s.commit()
    assert emitted == [(tid, "lead.created", {"id": "1"})]

    s.begin()
    s.info.setdefault(webhooks._PENDING_KEY, []).append((tid, "lead.created", {"id": "2"}))
    s.rollback()
    s.begin()
    s.commit()
    assert len(emitted) == 1  # the rolled-back event was dropped
    s.close()


# --------------------------------------------------------------------------- API keys
def test_api_key_format_and_hash() -> None:
    raw = apikeys.generate_key()
    assert raw.startswith("ofd_live_") and len(raw) > 40
    assert apikeys.hash_key(raw) == hashlib.sha256(raw.encode()).hexdigest()
    assert apikeys.generate_key() != raw


async def test_resolve_rejects_foreign_prefix_without_db() -> None:
    assert await apikeys.resolve_key(None, "sk-not-ours") is None  # type: ignore[arg-type]
    assert await apikeys.resolve_key(None, "") is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------- endpoint auth
def test_public_api_requires_key() -> None:
    r = client.get("/v1/me")
    assert r.status_code == 401
    r = client.get("/v1/me", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_integrations_require_login() -> None:
    assert client.get("/integrations/webhooks").status_code == 401
    assert client.post("/integrations/api-keys", json={"name": "n8n"}).status_code == 401


def test_event_catalog_is_public() -> None:
    r = client.get("/integrations/events")
    assert r.status_code == 200
    assert {e["type"] for e in r.json()} == set(webhooks.EVENT_TYPES)
