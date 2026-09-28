"""Ready-to-import n8n workflows, personalised per webhook.

The "Connect n8n" flow creates the OpenFrontDesk webhook and hands back the matching workflow file with
that webhook's signing secret and a unique path already filled in, so the user only imports it and
connects their own Google, Slack or email account. The source templates live in `integrations/n8n`.
"""

from __future__ import annotations

import copy
import json
import secrets
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from ofd.core.exceptions import NotFound, ValidationError

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "integrations" / "n8n"
SECRET_PLACEHOLDER = "whsec_REPLACE_ME"

TEMPLATES: dict[str, dict] = {
    "leads": {
        "file": "lead-to-sheets-and-slack.json",
        "name": "New leads to Google Sheets and Slack",
        "description": "Every lead becomes a row in a Google Sheet and a message in a Slack channel.",
        "events": ["lead.created"],
        "needs": ["A Google account with a sheet", "A Slack workspace"],
    },
    "calls": {
        "file": "call-summary-email.json",
        "name": "Email every call transcript",
        "description": "When a call ends, its outcome and full transcript arrive by email.",
        "events": ["call.completed"],
        "needs": ["An email account n8n can send from (SMTP)"],
    },
}


@lru_cache
def _load(key: str) -> dict:
    meta = TEMPLATES.get(key)
    if meta is None:
        raise NotFound(f"Unknown template: {key}")
    return json.loads((TEMPLATE_DIR / meta["file"]).read_text(encoding="utf-8"))


def n8n_base(url: str) -> str:
    """Accept "https://n8n.example.com", with or without a trailing slash or a pasted webhook path."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError("Enter your n8n address, starting with http:// or https://")
    base = url.split("/webhook", 1)[0]
    return base.rstrip("/")


def new_path(key: str) -> str:
    return f"ofd-{key}-{secrets.token_hex(4)}"


def build(key: str, *, secret: str, path: str, workspace: str) -> dict:
    """A copy of the template with the secret, the webhook path and a fresh webhook id filled in."""
    wf = copy.deepcopy(_load(key))
    wf.pop("id", None)  # let n8n assign one, so a second copy never overwrites the first
    wf["name"] = f"{wf['name']} ({workspace})"
    placed_secret = placed_path = False
    for node in wf["nodes"]:
        if node["type"] == "n8n-nodes-base.webhook":
            node["parameters"]["path"] = path
            node["webhookId"] = str(uuid.uuid4())
            placed_path = True
        code = node.get("parameters", {}).get("jsCode", "")
        if SECRET_PLACEHOLDER in code:
            node["parameters"]["jsCode"] = code.replace(SECRET_PLACEHOLDER, secret)
            placed_secret = True
    if not (placed_secret and placed_path):  # the template file changed shape
        raise RuntimeError(f"Template {key} has no webhook node or secret placeholder")
    return wf


def catalog() -> list[dict]:
    return [
        {"key": k, **{f: v[f] for f in ("name", "description", "events", "needs")}}
        for k, v in TEMPLATES.items()
    ]
