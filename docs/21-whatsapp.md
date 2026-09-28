# 21 — WhatsApp channel

Your receptionist can answer WhatsApp messages with the same knowledge, booking and lead capture as the
website chat. It remembers each customer's conversation for a day and logs every message in the
dashboard (**WhatsApp** in the sidebar).

## Two ways to connect WhatsApp

| | Self-hosted gateway (WA-AKG), available now | Official WhatsApp Business Platform (Meta Cloud API), planned |
|---|---|---|
| How it links | Scans a QR code like WhatsApp Web, with a normal WhatsApp number | Business verification with Meta and an approved number |
| Cost | Free (you host the gateway) | Meta's per-conversation pricing |
| Setup time | Minutes | Days (business verification) |
| Risk | Unofficial: WhatsApp can restrict numbers that send automated messages | Sanctioned; Meta allows purpose-specific bots such as support and bookings |
| Best for | Pilots, small volumes, a dedicated number | Production at volume |

OpenFrontDesk ships the WA-AKG provider today. The connection model is provider-based, so the official
API can be added behind the same screens later. Meta's 2026 policy bans general-purpose AI chatbots on
its business platform but explicitly allows purpose-specific bots for customer support and bookings, which
is what this receptionist is.

## How it works

```
 customer's WhatsApp ──► WA-AKG gateway ──signed POST──► OpenFrontDesk /channels/whatsapp/inbound/{id}
                                                              │ acknowledge at once
                                                              ▼ (background)
                                  verify, filter, de-duplicate, rate-limit, recall the last turns
                                                              ▼
                                  grounded chat brain (knowledge, availability, booking, take message)
                                                              ▼
 customer's WhatsApp ◄── WA-AKG gateway ◄── POST /api/messages/{session}/{number}/send
```

1. **Connect.** In the dashboard you enter the gateway address, the session ID and a WA-AKG API key.
   OpenFrontDesk checks the session, then registers a webhook on the gateway pointing at its inbound URL,
   with a secret it generates. The API key is stored encrypted; the secret never leaves the two systems.
2. **Receive.** WA-AKG sends each new message as a `message.received` event, signed with
   `X-Webhook-Signature: sha256=<HMAC-SHA256 of the body>`. OpenFrontDesk rejects anything unsigned or
   wrongly signed, and answers the gateway immediately so its 10-second timeout never trips while the
   model is thinking.
3. **Answer.** The message goes through the same chat brain as the website widget, with the customer's
   WhatsApp number and name as context (so bookings and messages use that number without asking), and
   with the last 10 turns of that customer's conversation from the past 24 hours.
4. **Reply and log.** The answer is sent back through the gateway. Both messages appear under WhatsApp in
   the dashboard, and any lead or booking created fires the usual email alerts and webhooks.

### What it answers and what it ignores

| Message | Behaviour |
|---|---|
| Text | Answered |
| Image, video or document with a caption | The caption is answered |
| Voice note, or media without a caption | Polite reply asking the customer to type |
| Stickers, reactions, locations, contacts | Ignored |
| Group chats, status updates, channels | Ignored |
| Your own messages (sent from the linked phone) | Ignored |
| The same message delivered twice | Answered once |
| Events older than 10 minutes | Ignored (replay protection) |

A single customer is limited to `WHATSAPP_MAX_PER_SENDER_PER_10MIN` answered messages (default 20) to cap
model spend if someone floods the number.

## Set up WA-AKG

WA-AKG is an MIT-licensed, self-hosted WhatsApp gateway built on Baileys:
<https://github.com/mrifqidaffaaditya/WA-AKG>. It needs Node.js 20+ and MySQL or PostgreSQL; its own Docker
Compose file runs both.

1. Get it and configure it:
   ```bash
   git clone https://github.com/mrifqidaffaaditya/WA-AKG.git
   cd WA-AKG
   cp .env.example .env    # set MYSQL_ROOT_PASSWORD, AUTH_SECRET, ADMIN_EMAIL, BASE_URL
   ```
   WA-AKG listens on port **3000** by default, which is also the OpenFrontDesk web app's development port.
   On the same machine, change WA-AKG's published port, for example `"3100:3000"` in its
   `docker-compose.yml`, and set `BASE_URL=http://localhost:3100`.
2. Start it:
   ```bash
   docker compose up -d
   ```
3. Open WA-AKG (for example `http://localhost:3100`), sign in, and create a **session** (for example
   `frontdesk`).
4. On the phone that owns the number, open WhatsApp, then **Linked devices**, then **Link a device**, and
   scan the session's QR code. Use a dedicated business number, not your personal one.
5. In WA-AKG, create an **API key**.

## Connect it to OpenFrontDesk

In the dashboard, open **WhatsApp** and fill in:

| Field | Value |
|---|---|
| Gateway address | Where OpenFrontDesk's API can reach WA-AKG (see below) |
| Session ID | The session you created, for example `frontdesk` |
| API key | The WA-AKG API key |

Click **Connect WhatsApp**, then **Test connection**. The test asks WA-AKG to deliver a signed test event
to OpenFrontDesk and reports the result, which proves both directions: OpenFrontDesk can reach the gateway
with your key, and the gateway can reach OpenFrontDesk with a valid signature.

Send a WhatsApp message to the linked number from another phone. The reply arrives within a few seconds,
and the conversation appears on the WhatsApp page.

### Addresses: local and production

Both systems must be able to reach each other.

**Local (both on your computer, in Docker):**

- Gateway address: `http://host.docker.internal:3100` (how the API container reaches a port on your
  computer).
- In OpenFrontDesk's `.env`: `INBOUND_BASE_URL=http://host.docker.internal:8081` (how WA-AKG's container
  reaches OpenFrontDesk's API) and `WEBHOOK_ALLOW_PRIVATE=true` (both addresses are private). Restart the
  API after changing `.env`: `docker compose up -d api`.

**Production:**

- Gateway address: its public HTTPS address, for example `https://wa.yourbusiness.com`.
- Leave `INBOUND_BASE_URL` empty so the inbound URL uses `PUBLIC_BASE_URL`, for example
  `https://api.yourbusiness.com`.
- Keep `WEBHOOK_ALLOW_PRIVATE=false`.

The dashboard shows the exact inbound URL the gateway calls ("Gateway sends to").

## Security

- **Signed inbound events.** Every event must carry a valid HMAC-SHA256 signature made with the secret
  OpenFrontDesk created for that connection. Unsigned or wrongly signed requests get HTTP 401.
- **Replay and duplicates.** Events older than 10 minutes are ignored, and each message ID is answered at
  most once.
- **Credentials at rest.** The WA-AKG API key is encrypted with a key derived from `SECRET_KEY`. The
  dashboard only ever shows its last four characters. Changing `SECRET_KEY` means reconnecting WhatsApp.
- **Outbound calls.** The gateway address passes the same private-address guard as webhooks.
- **Protect the gateway itself.** WA-AKG controls your WhatsApp number. Use a strong admin password,
  restrict or disable its Swagger page (`NEXT_PUBLIC_SWAGGER_ENABLED=false`) on a public server, and serve
  it over HTTPS.

## Limitations

- Unofficial connection: numbers can be restricted by WhatsApp. Keep volumes modest and use a dedicated
  number. Move to the official platform for production at scale.
- No group chats, and voice notes are not transcribed (customers are asked to type).
- Memory lasts 24 hours and 10 turns per customer.
- There is no "pause the bot while a human replies" switch yet. If you reply from the phone, the
  receptionist still answers the customer's next message.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `INBOUND_BASE_URL` | empty (uses `PUBLIC_BASE_URL`) | The API address gateways use to reach OpenFrontDesk |
| `WHATSAPP_MAX_PER_SENDER_PER_10MIN` | `20` | Answered messages per customer per 10 minutes |
| `WHATSAPP_HISTORY_TURNS` | `10` | Conversation turns remembered per customer (24 hours) |
| `WEBHOOK_ALLOW_PRIVATE` | `false` | Allow private gateway and receiver addresses (local setups only) |

## API

Owner or admin:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/channels/whatsapp` | Connection details and the gateway's live session status |
| `PUT` | `/channels/whatsapp` | Connect or reconnect: `{base_url, session_id, api_key}` |
| `DELETE` | `/channels/whatsapp` | Disconnect and remove the webhook from the gateway |
| `POST` | `/channels/whatsapp/test` | Two-way connection test |
| `GET` | `/channels/whatsapp/messages?limit=` | Recent messages, newest first |

Public (signed by the gateway): `POST /channels/whatsapp/inbound/{connection_id}`.

## Verification

- Unit tests cover the signature scheme, message filtering (own messages, groups, statuses, stale events,
  media, stickers), the gateway client (paths, headers, error mapping) and key encryption.
- End to end against a gateway that implements WA-AKG's API exactly (built from its source): wrong key and
  wrong session are refused clearly; connecting registers the webhook; the two-way test passes; "How much
  is a sports massage?" is answered from the knowledge base ("$70 and lasts 45 minutes"); the follow-up
  "And how long does it take?" is answered from memory; a duplicate is answered once; a voice note gets the
  please-type reply; a forged signature gets 401; disconnecting removes the gateway webhook.
- Linking a real phone by QR code is the one step that needs a person with the phone.
