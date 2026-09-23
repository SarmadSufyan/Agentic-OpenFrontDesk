# 15 — API Reference

REST + JSON. Auth via `Authorization: Bearer <jwt>`. Interactive OpenAPI at `/docs` (Swagger) and
`/redoc`. All non-auth routes are tenant-scoped by the token's active tenant. This lists the v1 surface;
✅ = implemented, ⬜ = planned (phase noted).

## Health
- `GET /health` — liveness ✅ (P0)
- `GET /health?deep=1` — DB + Redis readiness ⬜ (P0)

## Auth  (P3)
- `POST /auth/signup` — create user + first tenant ⬜
- `POST /auth/login` — issue access + refresh ⬜
- `POST /auth/refresh` — rotate tokens ⬜
- `GET  /auth/me` — current user + memberships ⬜

## Tenants  (P3)
- `GET/PATCH /tenants/current` — profile, hours, timezone, settings ⬜
- `POST /tenants/switch` — change active tenant ⬜
- `POST /tenants/current/members` — invite ⬜

## Agents  (P2/P3)
- `GET/PUT /agents/current` — voice, greeting, persona, escalation & booking rules ⬜

## Knowledge  (P2)
- `POST /knowledge` — upload file / paste text / submit URL → ingestion job ⬜
- `GET  /knowledge` — list docs + status ⬜
- `POST /knowledge/{id}/reindex` — re-run ingestion ⬜
- `DELETE /knowledge/{id}` — remove doc + chunks ⬜
- `GET  /knowledge/search?q=` — debug retrieval (test console) ⬜

## Calls  (P2/P3)
- `GET /calls` — list (filters: outcome, date) ⬜
- `GET /calls/{id}` — detail: transcript, tool trace, recording, latency, cost ⬜

## Bookings & Leads  (P2/P3)
- `GET /bookings` · `GET /leads` — list/export ⬜

## Analytics  (P3)
- `GET /analytics/overview` — KPIs (calls, bookings, deflection, minutes, latency) ⬜

## LiveKit / Voice  (P1)
- `GET /livekit/token?room=test` — mint a scoped browser-test token ⬜

## Integrations  (P2/P3)
- `POST /integrations/{type}` — connect Cal.com / Google / SMS / CRM ⬜
- `GET  /integrations` — list (secrets never returned) ⬜

## Webhooks  (P2/P4)
- `POST /webhooks/telephony` — inbound call/SIP events ⬜
- `POST /webhooks/calcom` — booking sync ⬜

## Automations (SaaS M3), implemented
Full guide, event payloads and signature verification: [17-automations.md](17-automations.md).

Management (JWT, owner/admin):
- `GET /integrations/events` — event catalog
- `GET|POST /integrations/webhooks`, `PATCH|DELETE /integrations/webhooks/{id}`
- `POST /integrations/webhooks/{id}/rotate-secret`, `POST /integrations/webhooks/{id}/test`,
  `GET /integrations/webhooks/{id}/deliveries`
- `GET|POST /integrations/api-keys`, `DELETE /integrations/api-keys/{id}`

Public API (workspace API key in `X-API-Key` or `Authorization: Bearer`):
- `GET /v1/me` · `POST /v1/chat` · `GET /v1/knowledge/search`
- `GET|POST /v1/leads` · `GET /v1/availability` · `GET|POST /v1/bookings`
- `GET /v1/calls` · `GET /v1/calls/{id}`

## Contact and admin inbox (SaaS M4), implemented
Guide: [18-contact-and-personalization.md](18-contact-and-personalization.md).

Public: `GET /contact` (form page) · `GET /contact/options` · `POST /contact`

Admin (`ADMIN_EMAILS`):
- `GET /admin/contact-requests` · `GET|PATCH|DELETE /admin/contact-requests/{id}`
- `POST /admin/contact-requests/{id}/scheduling-email`
- `GET|POST /admin/allowlist`, `DELETE /admin/allowlist/{email}` · `GET /admin/voice/sessions`

## Conventions
- Errors: JSON problem shape `{ "error": { "code", "message", "details" } }`.
- Pagination: `?limit=&cursor=`. Timestamps ISO-8601 UTC. IDs are UUIDs.
