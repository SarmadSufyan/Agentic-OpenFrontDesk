"""Smoke test: the app boots and liveness returns healthy (no DB needed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ofd import __version__
from ofd.api.app import app

client = TestClient(app)


def test_health_liveness() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["env"]


def test_openapi_available() -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/health" in resp.json()["paths"]
