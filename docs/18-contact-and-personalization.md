# 18 — Custom solutions: contact form, admin inbox, scheduling

OpenFrontDesk is free and self-serve. Some companies need more: a WhatsApp assistant, an HR or internal
helpdesk bot, a chatbot wired into their CRM, or automations built on their own n8n / Zapier accounts.
This feature turns that interest into a scheduled call with as little friction as possible:

1. The company fills in the form at `/contact` (what they need, team size, budget, a description).
2. They immediately see a confirmation and, when `SCHEDULING_URL` is set, a **"Choose a time"** button
   that opens your Cal.com / Calendly page **prefilled with their name and email**. A confirmation email
   with the same link follows.
3. The admins are notified by email (Reply-To is the requester, so "reply" just works) and optionally in
   Slack / n8n / Zapier through `CONTACT_WEBHOOK_URL`.
4. In the dashboard's **Admin** tab, admins work the request: status, internal notes, meeting time and
   link, and a one-click **scheduling email** with a personal note.

```
 visitor ──> /contact form ──> POST /contact ──> contact_request (Postgres)
                  │                                  │ after commit (background)
                  │                                  ├──> email to admins (Reply-To: requester)
                  │                                  ├──> confirmation email to requester (+ booking link)
                  │                                  └──> CONTACT_WEBHOOK_URL (Slack / n8n / Zapier)
                  └── instant "Choose a time" button (prefilled Cal.com / Calendly link)

 admin ──> /app#admin ──> /admin/contact-requests (filter, search, status, notes, meeting)
                              └──> scheduling email (personal note + prefilled booking link)
```

## What the form collects

| Field | Notes |
|---|---|
| Name, work email | Required. Email must be a plain address (letters, digits, `._%+-`); anything else is rejected |
| Company, website, phone | Optional, single line (newlines are collapsed so they cannot reach email headers) |
| Team size | `1-10`, `11-50`, `51-200`, `201-1000`, `1000+` |
| Needs | Any of `whatsapp`, `chatbot`, `voice`, `hr_assistant`, `automation`, `crm`, `other` |
| Budget | `under_1k`, `1k_5k`, `5k_20k`, `20k_plus`, `not_sure` |
| Message | Required, 10 to 5000 characters |

The choices are served by `GET /contact/options`, so the page (and the future Next.js frontend) always
match what the API accepts. `/contact?need=whatsapp` preselects a need, which is handy for "Talk to us
about WhatsApp" links on a pricing or feature page.

If a signed-in user submits the form (the page sends the dashboard token when present), the request is
linked to their account and workspace, and the form prefills their name, email, and workspace name.

## Abuse controls

| Control | Behaviour |
|---|---|
| Honeypot | A visually hidden `company_fax` field. Bots that fill it get a normal-looking 202 and nothing is stored |
| Per-IP limit | `CONTACT_RATE_LIMIT_PER_HOUR` (default 5) per client IP, Redis fixed window, 429 after that |
| Link stuffing | More than four URLs in the message: stored with status `spam`, no emails, no booking link returned |
| Double submit | Same email and message within 10 minutes returns the earlier request instead of a duplicate |
| Privacy | The IP is stored only as a salted SHA-256 hash; admins can permanently delete a request |

Behind nginx or a load balancer, set `TRUST_PROXY_HEADERS=true` so the limit uses the real client IP from
`X-Forwarded-For`. Leave it `false` otherwise, since the header is trivially spoofed by clients.

## Email

Plain SMTP through the standard library, so any provider works: a Gmail or Workspace app password, Brevo,
Resend, Amazon SES, Postmark, or your host's SMTP. Email is optional: with `SMTP_HOST` empty, requests are
still stored and visible in the inbox, notifications are skipped (and logged), and the scheduling-email
button explains what to configure.

Sending never blocks the request: notifications run as a background task after the row is committed, and
failures are logged, never raised.

Emails sent:

| When | To | Reply-To |
|---|---|---|
| New request | `CONTACT_NOTIFY_EMAILS` (defaults to `ADMIN_EMAILS`) | The requester |
| New request | The requester (confirmation, booking link if configured) | First notify address |
| Admin clicks "Send email" | The requester (personal note + prefilled booking link) | That admin |

### Local testing with Mailpit

```bash
docker compose --profile mail up -d mailpit     # inbox UI at http://localhost:8025
```

In `.env`: `SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_STARTTLS=false`,
`SMTP_FROM=OpenFrontDesk <hello@openfrontdesk.local>`. Every email the API sends then shows up in Mailpit
instead of a real inbox.

## Admin inbox

The **Admin** tab appears in the dashboard only for platform admins (emails listed in `ADMIN_EMAILS`;
`GET /auth/me` returns `is_admin`). The link in notification emails, `/app#admin`, opens it directly.

- Counters for new, contacted, scheduled and won requests; filter by status; search across name, email,
  company and message.
- Detail view: every field, the message, status, meeting time and link, internal notes (never shown to
  the requester), who handled it last, and when they were last contacted.
- Setting a meeting time on a new or contacted request moves it to `scheduled` automatically.
- **Send a scheduling email**: a personal note plus the booking link prefilled with the requester's name
  and email. Marks a new request as contacted.
- **Delete** removes the request permanently (spam, or when the person asks for their data to be deleted).

The same tab also manages voice access from M1: live sessions against the concurrency cap, the waiting
queue, and the priority allowlist (people added there skip the voice queue).

Statuses: `new`, `contacted`, `scheduled`, `won`, `lost`, `spam`.

## API

Public:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/contact` | The form page |
| `GET` | `/contact/options` | Needs, team sizes, budgets, and whether a booking link is configured |
| `POST` | `/contact` | Submit. `202` with `{id, scheduling_url}`; `422` on invalid input; `429` when rate limited |

Admin (JWT of a user in `ADMIN_EMAILS`):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/contact-requests?status=&q=&limit=&offset=` | List with total and per-status counts |
| `GET` / `PATCH` / `DELETE` | `/admin/contact-requests/{id}` | Read / update status, notes, meeting / delete |
| `POST` | `/admin/contact-requests/{id}/scheduling-email` | Body `{"message": "...", "link": "..."}` (both optional) |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SCHEDULING_URL` | empty | Your Cal.com or Calendly link; enables the instant booking button and scheduling emails |
| `CONTACT_NOTIFY_EMAILS` | `ADMIN_EMAILS` | Who is notified of new requests |
| `CONTACT_WEBHOOK_URL` | empty | Slack incoming webhook, n8n or Zapier URL; receives `{text, event, contact}` |
| `CONTACT_RATE_LIMIT_PER_HOUR` | `5` | Submissions per client IP per hour |
| `TRUST_PROXY_HEADERS` | `false` | Use `X-Forwarded-For` for the client IP (only behind a trusted proxy) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base for links in emails |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `SMTP_SSL` | | SMTP settings; empty host disables email |

## Security notes

- Everything a prospect types is rendered in the admin's browser, so it is treated as hostile: the email
  pattern excludes quotes, brackets and spaces; the dashboard escapes all text including quotes; and no
  user-supplied value is placed inside an inline event handler (the allowlist uses `data-` attributes, and
  "Reply by email" is a plain `mailto:` link). A unit test pins the email rule with JavaScript-breakout
  payloads.
- Single-line fields collapse whitespace, so a newline in a company name cannot add an email header.
- The operator-configured `CONTACT_WEBHOOK_URL` is trusted configuration and is not subject to the
  tenant webhook SSRF guard.

## Code map

| Concern | Location |
|---|---|
| Model (`contact_request`) | `src/ofd/models/contact.py` |
| Validation, choices, statuses | `src/ofd/schemas/contact.py` |
| Intake, dedupe, spam, notifications, inbox operations | `src/ofd/services/contact.py` |
| SMTP sender | `src/ofd/services/mailer.py` |
| Public endpoints and form page | `src/ofd/api/routers/contact.py`, `src/ofd/api/contactpage.py` |
| Admin endpoints | `src/ofd/api/routers/admin.py` |
| Admin tab | `src/ofd/api/dashboard.py` |
| Tests | `tests/test_contact.py` |
