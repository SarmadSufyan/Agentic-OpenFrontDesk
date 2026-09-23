"""Unit tests for the custom-solutions contact flow: validation and sanitising, spam controls,
scheduling links, the mailer, and endpoint auth. No database, SMTP server or network required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ofd.api.app import app
from ofd.core.config import settings
from ofd.schemas.contact import ContactIn, ContactUpdate
from ofd.services import contact as contact_svc
from ofd.services import mailer

client = TestClient(app)

VALID = {
    "name": "Amira Khan",
    "email": "Amira@Example.co.uk",
    "company": "Bright Smile Dental",
    "needs": ["whatsapp", "automation", "whatsapp"],
    "team_size": "11-50",
    "budget": "1k_5k",
    "message": "We get about 80 WhatsApp messages a day and want them answered.",
}


# --------------------------------------------------------------------------- validation
def test_valid_request_is_normalised() -> None:
    body = ContactIn(**VALID)
    assert body.email == "amira@example.co.uk"
    assert body.needs == ["automation", "whatsapp"]


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "a@b",
        "x'+alert(1)+'@evil.com",  # would break out of a JS string in the admin UI
        'x"onmouseover=alert(1)@evil.com',
        "space in@example.com",
        "<a>@example.com",
    ],
)
def test_rejects_unsafe_or_invalid_emails(email: str) -> None:
    with pytest.raises(ValidationError):
        ContactIn(**{**VALID, "email": email})


def test_rejects_whitespace_only_name_and_short_message() -> None:
    with pytest.raises(ValidationError):
        ContactIn(**{**VALID, "name": "   "})
    with pytest.raises(ValidationError):
        ContactIn(**{**VALID, "message": "   hi     "})


def test_single_line_fields_cannot_inject_headers() -> None:
    body = ContactIn(**{**VALID, "company": "Acme\r\nBcc: victim@example.com", "name": "A\nB"})
    assert "\n" not in body.company and "\r" not in body.company
    assert body.name == "A B"


def test_rejects_unknown_choices() -> None:
    for field, value in [("needs", ["teleport"]), ("team_size", "5"), ("budget", "lots")]:
        with pytest.raises(ValidationError):
            ContactIn(**{**VALID, field: value})


def test_update_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate(status="archived")
    assert ContactUpdate(status="won").status == "won"


# --------------------------------------------------------------------------- helpers
def test_link_stuffed_message_is_spam() -> None:
    spammy = " ".join(f"https://spam{i}.example" for i in range(6))
    assert contact_svc.looks_like_spam(ContactIn(**{**VALID, "message": spammy}))
    assert not contact_svc.looks_like_spam(ContactIn(**VALID))


def test_scheduling_link_is_prefilled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SCHEDULING_URL", "https://cal.com/team/intro?duration=30")
    url = contact_svc.scheduling_link("Amira Khan", "amira@example.co.uk")
    assert url.startswith("https://cal.com/team/intro?")
    assert (
        "duration=30" in url and "name=Amira+Khan" in url and "email=amira%40example.co.uk" in url
    )


def test_scheduling_link_absent_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SCHEDULING_URL", "")
    assert contact_svc.scheduling_link("A", "a@b.co") is None
    assert contact_svc.scheduling_link("A", "a@b.co", base="https://calendly.com/x").startswith(
        "https://calendly.com/x?"
    )


def test_ip_is_hashed_not_stored() -> None:
    h = contact_svc.hash_ip("203.0.113.9")
    assert h and "203.0.113.9" not in h and len(h) == 64
    assert h == contact_svc.hash_ip("203.0.113.9")
    assert contact_svc.hash_ip(None) is None


def test_notify_recipients_default_to_admins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CONTACT_NOTIFY_EMAILS", "")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "B@x.com, a@x.com")
    assert settings.contact_notify_emails == ["a@x.com", "b@x.com"]
    monkeypatch.setattr(settings, "CONTACT_NOTIFY_EMAILS", "sales@x.com")
    assert settings.contact_notify_emails == ["sales@x.com"]


# --------------------------------------------------------------------------- mailer
async def test_mailer_is_a_no_op_without_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    assert not mailer.is_configured()
    assert await mailer.send(to="a@b.co", subject="s", text="t") is False


async def test_mailer_builds_and_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_FROM", "OpenFrontDesk <hello@ofd.test>")
    sent = []
    monkeypatch.setattr(mailer, "_deliver", lambda msg: sent.append(msg))
    ok = await mailer.send(to=["a@b.co", ""], subject="Hi", text="Body", reply_to="me@ofd.test")
    assert ok and len(sent) == 1
    msg = sent[0]
    assert msg["To"] == "a@b.co" and msg["Reply-To"] == "me@ofd.test"
    assert msg["From"] == "OpenFrontDesk <hello@ofd.test>" and "@ofd.test>" in msg["Message-ID"]


async def test_mailer_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_FROM", "hello@ofd.test")

    def boom(msg):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr(mailer, "_deliver", boom)
    assert await mailer.send(to="a@b.co", subject="s", text="t") is False


# --------------------------------------------------------------------------- endpoints
def test_contact_page_and_options_are_public() -> None:
    page = client.get("/contact")
    assert page.status_code == 200 and 'name="company_fax"' in page.text
    opts = client.get("/contact/options").json()
    assert "whatsapp" in opts["needs"] and "11-50" in opts["team_sizes"]


def test_honeypot_submission_is_accepted_but_not_stored() -> None:
    r = client.post("/contact", json={**VALID, "company_fax": "http://spam.example"})
    assert r.status_code == 202 and r.json()["id"] is None


def test_invalid_submission_is_rejected() -> None:
    assert client.post("/contact", json={**VALID, "email": "nope"}).status_code == 422


def test_admin_inbox_requires_login() -> None:
    assert client.get("/admin/contact-requests").status_code == 401
    assert (
        client.patch(
            "/admin/contact-requests/00000000-0000-0000-0000-000000000000", json={"status": "won"}
        ).status_code
        == 401
    )
