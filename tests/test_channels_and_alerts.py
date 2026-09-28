"""Unit tests for the WhatsApp channel, email alerts and n8n template personalisation.
No database, gateway, SMTP server or network required."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError, ValidationError
from ofd.services import n8n_templates, notifications, secretbox, whatsapp


# --------------------------------------------------------------------------- secretbox
def test_secretbox_round_trip_and_tamper() -> None:
    token = secretbox.encrypt("wa-akg-key-123")
    assert "wa-akg-key-123" not in token
    assert secretbox.decrypt(token) == "wa-akg-key-123"
    with pytest.raises(ValueError):
        secretbox.decrypt(token[:-4] + "AAAA")


# --------------------------------------------------------------------------- WA-AKG signature
def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_matches_wa_akg_scheme() -> None:
    body = b'{"event":"message.received"}'
    assert whatsapp.verify_signature("s3cret", body, _sign("s3cret", body))
    assert not whatsapp.verify_signature("s3cret", body, _sign("other", body))
    assert not whatsapp.verify_signature("s3cret", body + b" ", _sign("s3cret", body))
    assert not whatsapp.verify_signature("s3cret", body, None)


# --------------------------------------------------------------------------- inbound filtering
def _event(**data) -> dict:
    base = {
        "key": {"id": "3EB0ABC", "remoteJid": "923001234567@s.whatsapp.net", "fromMe": False},
        "from": "923001234567@s.whatsapp.net",
        "pushName": "Ayesha",
        "isGroup": False,
        "chatType": "PERSONAL",
        "type": "TEXT",
        "content": "Do you have Sunday slots?",
    }
    base.update(data)
    return {
        "event": "message.received",
        "sessionId": "shop1",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data": base,
    }


def test_text_message_is_answered() -> None:
    msg = whatsapp.parse_inbound(_event())
    assert msg == {
        "mode": "answer",
        "text": "Do you have Sunday slots?",
        "phone": "923001234567",
        "jid": "923001234567@s.whatsapp.net",
        "name": "Ayesha",
        "message_id": "3EB0ABC",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"key": {"id": "x", "fromMe": True}},  # our own reply echoing back
        {"isGroup": True},
        {"chatType": "STATUS"},
        {"from": "100429287395370@lid"},  # not a phone address
        {"type": "STICKER", "content": ""},
    ],
)
def test_ignored_events(change: dict) -> None:
    assert whatsapp.parse_inbound(_event(**change)) is None


def test_other_event_types_and_stale_events_are_ignored() -> None:
    assert whatsapp.parse_inbound({**_event(), "event": "message.status"}) is None
    old = _event()
    old["timestamp"] = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    assert whatsapp.parse_inbound(old) is None


def test_media_uses_caption_or_asks_for_text() -> None:
    captioned = whatsapp.parse_inbound(_event(type="IMAGE", content="How much is this?"))
    assert captioned["mode"] == "answer" and captioned["text"] == "How much is this?"
    assert whatsapp.parse_inbound(_event(type="AUDIO", content=""))["mode"] == "text_only"


def test_phone_helpers() -> None:
    assert whatsapp.phone_digits("6281234567@s.whatsapp.net") == "6281234567"
    assert whatsapp.phone_digits("120363@g.us") is None
    assert whatsapp.me_phone({"me": {"id": "6281234567:12@s.whatsapp.net"}}) == "6281234567"
    assert whatsapp.me_phone({"me": None}) is None
    assert whatsapp.gateway_base("https://wa.example.com/api/") == "https://wa.example.com"
    with pytest.raises(ValidationError):
        whatsapp.gateway_base("wa.example.com")


def test_inbound_url_prefers_inbound_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://api.example.com")
    monkeypatch.setattr(settings, "INBOUND_BASE_URL", "")
    assert whatsapp.inbound_url("c1").startswith(
        "https://api.example.com/channels/whatsapp/inbound/"
    )  # type: ignore[arg-type]
    monkeypatch.setattr(settings, "INBOUND_BASE_URL", "http://host.docker.internal:8081/")
    assert (
        whatsapp.inbound_url("c1")
        == "http://host.docker.internal:8081/channels/whatsapp/inbound/c1"
    )  # type: ignore[arg-type]


# --------------------------------------------------------------------------- gateway client
_REAL_CLIENT = httpx.AsyncClient  # captured once, so repeated mocks never wrap each other


def _mock(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_CLIENT(*args, **kwargs)

    monkeypatch.setattr(whatsapp.httpx, "AsyncClient", factory)


async def test_client_sends_text_with_key_and_encoded_jid(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"status": True, "data": {"id": "m1"}})

    _mock(monkeypatch, handler)
    client = whatsapp.WaAkgClient("http://gw:3000", "key-1")
    await client.send_text("shop1", "923001234567@s.whatsapp.net", "Hello!")
    req = seen[0]
    assert req.url.raw_path.decode() == "/api/messages/shop1/923001234567%40s.whatsapp.net/send"
    assert req.headers["X-API-Key"] == "key-1"
    assert json.loads(req.content) == {"message": {"text": "Hello!"}}


async def test_client_maps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock(
        monkeypatch,
        lambda r: httpx.Response(401, json={"status": False, "message": "Unauthorized"}),
    )
    with pytest.raises(ValidationError):
        await whatsapp.WaAkgClient("http://gw:3000", "bad").session("shop1")
    _mock(monkeypatch, lambda r: httpx.Response(500, json={"status": False, "message": "boom"}))
    with pytest.raises(ProviderError):
        await whatsapp.WaAkgClient("http://gw:3000", "k").session("shop1")


# --------------------------------------------------------------------------- n8n templates
def test_template_is_personalised_without_touching_the_source() -> None:
    wf = n8n_templates.build(
        "leads", secret="whsec_abc123", path="ofd-leads-1a2b3c4d", workspace="Lotus"
    )
    webhook = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
    code = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.code")["parameters"][
        "jsCode"
    ]
    assert webhook["parameters"]["path"] == "ofd-leads-1a2b3c4d"
    assert "const SECRET = 'whsec_abc123';" in code and n8n_templates.SECRET_PLACEHOLDER not in code
    assert "id" not in wf and wf["name"].endswith("(Lotus)")
    again = n8n_templates.build("leads", secret="whsec_other", path="p2", workspace="X")
    assert "whsec_abc123" not in json.dumps(again)  # the cached source stayed pristine
    assert again["nodes"][0]["webhookId"] != webhook["webhookId"]


def test_n8n_base_and_catalog() -> None:
    assert n8n_templates.n8n_base("https://n8n.example.com/") == "https://n8n.example.com"
    assert n8n_templates.n8n_base("http://n8n:5678/webhook/old-path") == "http://n8n:5678"
    with pytest.raises(ValidationError):
        n8n_templates.n8n_base("n8n.example.com")
    keys = {t["key"] for t in n8n_templates.catalog()}
    assert keys == {"leads", "calls"}


# --------------------------------------------------------------------------- email alerts
def test_alert_settings_validation() -> None:
    ok = notifications.validate([" Owner@Clinic.com ", "owner@clinic.com", ""], ["lead.created"])
    assert ok == {"emails": ["owner@clinic.com"], "events": ["lead.created"]}
    with pytest.raises(ValidationError):
        notifications.validate(["not an email"], [])
    with pytest.raises(ValidationError):
        notifications.validate([f"a{i}@x.com" for i in range(6)], [])
    with pytest.raises(ValidationError):
        notifications.validate([], ["lead.deleted"])
    assert notifications.read_settings(
        {"notifications": {"emails": ["a@x.com"], "events": ["x"]}}
    ) == {
        "emails": ["a@x.com"],
        "events": [],
    }


def test_alert_emails_read_well(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WEB_APP_URL", "https://app.example.com")
    subject, body = notifications.compose(
        "booking.created",
        {
            "customer_name": "Maya Chen",
            "customer_phone": "5550142",
            "service": "Cleaning",
            "start_at": "2026-09-29T05:30:00+00:00",
        },
        business="Bright Smile",
        timezone="Asia/Karachi",
    )
    assert (
        subject == "New booking: Cleaning, Tue 29 Sep 2026, 10:30"
    )  # shown in the business's zone
    assert "Maya Chen" in body and "https://app.example.com/dashboard/bookings" in body

    subject, body = notifications.compose(
        "lead.created",
        {"name": None, "phone": "5550199", "message": "Call me"},
        business="B",
        timezone="UTC",
    )
    assert subject == "New lead: 5550199" and "Call me" in body

    subject, body = notifications.compose(
        "call.completed",
        {
            "outcome": "message_taken",
            "duration_seconds": 95,
            "transcript": [{"role": "assistant", "text": "Hi!"}, {"role": "user", "text": "Hello"}],
        },
        business="B",
        timezone="UTC",
    )
    assert subject == "Call summary: message taken (1:35)"
    assert "Receptionist: Hi!" in body and "Caller: Hello" in body


async def test_alerts_do_nothing_without_email_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    await notifications.notify("t1", "lead.created", {})  # type: ignore[arg-type]  # returns quietly
    with pytest.raises(ValidationError):
        await notifications.send_test(tenant_name="B", emails=["a@x.com"])
