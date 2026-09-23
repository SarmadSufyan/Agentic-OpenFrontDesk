# 17 — Automations (webhooks, API keys, n8n / Zapier / Make)

OpenFrontDesk plugs into the automation tools small businesses already use. Two primitives close the
loop:

- **Outbound webhooks** push signed events the moment something happens (a lead is captured, an
  appointment is booked, a call ends, a document finishes indexing).
- **The public `/v1` API**, authenticated by a workspace API key, lets a workflow act back on the
  workspace: ask the agent a question, log a lead from another channel, check availability, book.

Together they turn the receptionist into a hub: "every new lead goes to a Google Sheet and Slack",
"email me each call transcript", "answer WhatsApp messages with the same trained agent". Ready-made n8n
workflows for exactly those three live in [`integrations/n8n`](../integrations/n8n).

```
 caller / visitor ──> voice agent / chat widget ──> lead, booking, call rows (Postgres)
                                                          │ commit
                                                          v
                                         signed webhook ──> n8n / Zapier / Make / your code
                                                                  │
                        /v1 API (X-API-Key) <─────────────────────┘  (ask, log, book)
```

## Events

| Type | When | `data` fields |
|---|---|---|
| `lead.created` | The agent took a message or captured contact details (voice, widget, or `/v1/leads`) | `id, name, phone, email, intent, message, tags, call_id` |
| `booking.created` | An appointment was booked (voice, widget, or `/v1/bookings`) | `id, customer_name, customer_phone, service, start_at, end_at, status, notes, call_id, agent_id` |
| `call.completed` | A voice call ended | `id, agent_id, direction, outcome, caller_number, started_at, ended_at, duration_seconds, summary, transcript[]` |
| `knowledge.ready` | A knowledge document finished indexing | `id, title, source_type, chunk_count, char_count` |
| `webhook.test` | You pressed "Test" in the dashboard | `message` |

Every delivery is a JSON envelope:

```json
{
  "id": "evt_3f0c9b2e0d8e4c1f9a7b6d5e4c3b2a19",
  "type": "lead.created",
  "created_at": "2026-09-23T13:02:11.482113+00:00",
  "tenant_id": "6f1c...",
  "data": { "id": "9a2e...", "name": "Jane Doe", "phone": "5550100", "intent": "new patient" }
}
```

An endpoint subscribes to a list of event types, or `["*"]` for all of them (the default).

## Delivery semantics

| Property | Behaviour |
|---|---|
| Headers | `X-OFD-Event`, `X-OFD-Delivery` (the event id), `X-OFD-Timestamp` (unix seconds), `X-OFD-Signature` |
| Signature | `sha256=` + hex HMAC-SHA256 of `"<timestamp>." + raw_body`, keyed by the endpoint secret |
| Timeout | `WEBHOOK_TIMEOUT_SECONDS` (default 10 s) per attempt; redirects are not followed |
| Retries | Up to `WEBHOOK_MAX_ATTEMPTS` (default 3) with exponential backoff, on network errors, 5xx, 408 and 429. Other 4xx responses are treated as permanent and not retried |
| Logging | Every delivery is recorded in `webhook_delivery` (event, result, status, attempts, duration, error) and shown in the dashboard |
| Auto-disable | After `WEBHOOK_DISABLE_AFTER_FAILURES` (default 25) consecutive failed deliveries, the endpoint is disabled; re-enabling resets the counter |
| Ordering | Not guaranteed. Use `created_at` and `id` to order and de-duplicate |

**Only committed data is announced.** Services queue events on the database session
(`webhooks.emit_on_commit`); a SQLAlchemy `after_commit` hook hands them to the dispatcher and a rollback
discards them. A request that fails after inserting a lead never notifies anyone about a lead that does
not exist.

**Never on the hot path.** Dispatch is fire-and-forget on the event loop, so a slow or dead receiver
cannot delay an API response or a live call. The API drains in-flight deliveries on shutdown and the
voice worker drains them before a call's job process exits.

**Known limitation.** Deliveries are in-process, not a durable queue: if the process is killed hard
mid-delivery, that delivery is lost (it is still visible as missing in the log). A Redis-backed outbox
with a replay button is on the roadmap; the envelope `id` is already stable so receivers can
de-duplicate once replays exist.

### Verifying signatures

Always verify against the **raw** request body, before parsing JSON, and reject stale timestamps to
block replays.

Python:

```python
import hashlib, hmac, time

def verify(secret: str, raw_body: bytes, timestamp: str, signature: str, tolerance: int = 300) -> bool:
    if abs(time.time() - int(timestamp)) > tolerance:
        return False
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)
```

Node.js:

```js
const crypto = require("crypto");

function verify(secret, rawBody, timestamp, signature, tolerance = 300) {
  if (Math.abs(Date.now() / 1000 - Number(timestamp)) > tolerance) return false;
  const expected = "sha256=" + crypto.createHmac("sha256", secret)
    .update(`${timestamp}.`).update(rawBody).digest("hex");
  return signature.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

### SSRF protection

A public SaaS that POSTs to user-supplied URLs must not become a proxy into its own network. Webhook
URLs must be `http(s)`, and the host is resolved and refused if any address is loopback, private
(RFC 1918), link-local (including the `169.254.169.254` cloud metadata service), reserved, multicast, or
unspecified. IPv4-mapped IPv6 addresses are unwrapped first. The check runs when the endpoint is saved
**and again at every delivery**, so a DNS record changed after registration cannot slip through.

Self-hosters who want to deliver to a receiver on their own network (for example the bundled n8n
container) set `WEBHOOK_ALLOW_PRIVATE=true`. Leave it `false` on any multi-tenant deployment.

## Managing webhooks

In the dashboard: **Integrations** tab. Add a URL, choose events, and copy the signing secret, which is
shown **once**. Each endpoint has Test, Log, Enable/Disable, Rotate (new secret, shown once), and Delete.

The same operations over the API (JWT, owner or admin role):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/integrations/events` | Event catalog |
| `GET` / `POST` | `/integrations/webhooks` | List (secret hint only) / create (returns the secret once) |
| `PATCH` / `DELETE` | `/integrations/webhooks/{id}` | Change URL, events, description, active flag / delete |
| `POST` | `/integrations/webhooks/{id}/rotate-secret` | New signing secret (returned once) |
| `POST` | `/integrations/webhooks/{id}/test` | Send `webhook.test` now and return the result |
| `GET` | `/integrations/webhooks/{id}/deliveries` | Last 50 deliveries |

## API keys

- Format `ofd_live_<43 random characters>`. Only the SHA-256 hash is stored; the plaintext is returned
  once at creation. The first characters (`ofd_live_XXXX`) are kept as a visible prefix.
- Send as `X-API-Key: <key>` or `Authorization: Bearer <key>`.
- A key is scoped to one workspace, rate limited per workspace (`API_RATE_LIMIT_PER_MIN`, default 120),
  records `last_used_at`, and can be revoked instantly. At most 20 active keys per workspace.
- Management: `GET/POST /integrations/api-keys`, `DELETE /integrations/api-keys/{id}` (owner/admin).
  Creating and revoking keys, and all webhook changes, are written to the audit log.

## Public API (`/v1`)

| Method | Path | What it does |
|---|---|---|
| `GET` | `/v1/me` | Which workspace this key belongs to (use it as a credential test) |
| `POST` | `/v1/chat` | Ask the trained agent; body `{"message": "...", "history": [...]}`; returns `{reply, sources}`. The agent can capture leads and book, as in the widget |
| `GET` | `/v1/knowledge/search?q=&k=` | Raw retrieval hits (text, score, source title) |
| `GET` / `POST` | `/v1/leads` | List leads / log a lead from another channel (tagged `api`, fires `lead.created`) |
| `GET` | `/v1/availability?date=&limit=` | Open appointment slots |
| `GET` / `POST` | `/v1/bookings` | List / create a booking (fires `booking.created`) |
| `GET` | `/v1/calls`, `/v1/calls/{id}` | Call history and full transcripts |

```bash
curl https://YOUR-HOST/v1/chat \
  -H "X-API-Key: $OFD_API_KEY" -H "Content-Type: application/json" \
  -d '{"message": "Do you take new patients on Saturdays?"}'
```

Errors use the standard shape `{"error": {"code", "message", "details"}}`: 401 for a missing, unknown,
or revoked key, 429 when the workspace limit is hit.

## n8n

Templates (import with **Workflows, Import from File**):

| File | Flow |
|---|---|
| `lead-to-sheets-and-slack.json` | Webhook, verify signature, if `lead.created`: append a Google Sheet row and post to Slack |
| `call-summary-email.json` | Webhook, verify signature, if `call.completed`: email the transcript |
| `whatsapp-ai-receptionist.json` | WhatsApp message in, `POST /v1/chat`, reply on WhatsApp with the agent's answer |

Setup is in [`integrations/n8n/README.md`](../integrations/n8n/README.md). Two details matter:

1. The webhook node has **Raw Body** enabled so the Code node can verify the exact bytes that were signed.
2. The Code node uses Node's `crypto` module. Self-hosted n8n must allow it with
   `NODE_FUNCTION_ALLOW_BUILTIN=crypto` (already set for the bundled container).

Bundled n8n for local work:

```bash
docker compose --profile automation up -d n8n     # UI at http://localhost:5678
```

From inside Docker, OpenFrontDesk reaches it at `http://n8n:5678/webhook/<path>`, a private address, so
set `WEBHOOK_ALLOW_PRIVATE=true` for that setup.

Verified against n8n 2.40: a correctly signed delivery passes the Code node (including non-ASCII
payloads), a wrong secret and a replayed timestamp are rejected, and a real delivery from the API
container to the n8n container succeeds end to end.

## Zapier and Make

- **Trigger:** Zapier "Webhooks by Zapier, Catch Raw Hook" or Make "Custom webhook". Paste its URL as an
  OpenFrontDesk webhook. Use the raw variant if you want to verify signatures in a code step.
- **Action:** Zapier "Webhooks by Zapier, Custom Request" or Make "HTTP, Make a request" to any `/v1`
  endpoint with the `X-API-Key` header.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `WEBHOOK_ALLOW_PRIVATE` | `false` | Allow delivery to private/internal addresses (self-hosting only) |
| `WEBHOOK_TIMEOUT_SECONDS` | `10` | Per-attempt timeout |
| `WEBHOOK_MAX_ATTEMPTS` | `3` | Attempts per delivery |
| `WEBHOOK_DISABLE_AFTER_FAILURES` | `25` | Consecutive failures before auto-disable |
| `API_RATE_LIMIT_PER_MIN` | `120` | Per-workspace API-key request limit |

## Code map

| Concern | Location |
|---|---|
| Models (`webhook_endpoint`, `webhook_delivery`, `api_key`) | `src/ofd/models/automation.py` |
| Signing, SSRF guard, retries, commit-gated dispatch | `src/ofd/services/webhooks.py` |
| Key generation, hashing, resolution | `src/ofd/services/apikeys.py` |
| Event emission | `services/leads.py`, `booking.py`, `calls.py`, `knowledge.py` |
| Management API / public API | `api/routers/integrations.py`, `api/routers/public_api.py` |
| API-key auth + rate limit | `api/deps.py` (`get_api_context`) |
| Tests | `tests/test_automations.py` |
