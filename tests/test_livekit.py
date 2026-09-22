"""Token endpoint + web routes wiring (no LiveKit creds needed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ofd.api.app import app

client = TestClient(app)


def test_token_requires_config(monkeypatch) -> None:
    # With no LiveKit creds configured, the endpoint returns a typed config error.
    # Force-clear here so the test is deterministic regardless of the ambient .env.
    from ofd.core.config import settings

    monkeypatch.setattr(settings, "LIVEKIT_URL", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_KEY", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "")
    resp = client.get("/livekit/token?room=ofd-test")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "config_error"


def test_test_page_served() -> None:
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "OpenFrontDesk" in resp.text
    assert "livekit-client" in resp.text


def test_landing_served() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Try a test call" in resp.text
