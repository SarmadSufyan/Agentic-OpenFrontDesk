# 06 — Data Model

Postgres + pgvector. UUID PKs, UTC timestamps, everything tenant-owned carries `tenant_id`. ORM models
in `ofd.models`; this doc is the authoritative schema reference.

## ERD (core)

```
tenant 1───* membership *───1 user
   │
   ├─1───* agent                (voice/persona/rules config)
   ├─1───* phone_number         (dialed number → tenant/agent)
   ├─1───* knowledge_doc 1───* doc_chunk(embedding)
   ├─1───* call 1───* call_event        (turns / tool calls / errors)
   │           └─1───0..1 booking
   │           └─1───0..1 lead
   ├─1───* booking
   ├─1───* lead
   ├─1───* integration          (calendar / sms / crm creds+config)
   └─1───* usage_event          (minutes, tokens, cost per call/provider)
```

## Enums
- `role`: `owner | admin | member`
- `doc_status`: `pending | processing | ready | failed`
- `source_type`: `pdf | docx | txt | text | url`
- `call_direction`: `inbound | outbound | test`
- `call_status`: `ringing | active | completed | failed`
- `call_outcome`: `booked | rescheduled | cancelled | message_taken | transferred | answered | abandoned | failed`
- `booking_status`: `confirmed | rescheduled | cancelled`
- `integration_type`: `calcom | google_calendar | twilio | telnyx | crm_webhook | slack`
- `provider_kind`: `stt | llm | tts | embeddings`

## Tables

### tenant
`id, name, slug (unique), vertical, timezone, business_hours (jsonb), address (jsonb), settings (jsonb),
plan, created_at, updated_at`

### user
`id, email (unique, citext), password_hash, name, is_active, created_at, updated_at`

### membership
`id, tenant_id, user_id, role, created_at` — unique (tenant_id, user_id)

### agent  (the configured receptionist)
`id, tenant_id, name, voice, greeting, persona (jsonb), tone, escalation_rules (jsonb),
booking_rules (jsonb), llm_overrides (jsonb), is_active, created_at, updated_at`

### phone_number
`id, tenant_id, agent_id, e164 (unique), provider (integration_type), provider_ref, status, created_at`

### knowledge_doc
`id, tenant_id, title, source_type, source_ref (path/url), status (doc_status), error, char_count,
chunk_count, created_at, updated_at`

### doc_chunk
`id, tenant_id, doc_id, chunk_index, text, embedding vector(DIM), metadata (jsonb), created_at`
— indexes: `ivfflat/hnsw` on `embedding`; btree on `(tenant_id, doc_id)`

### call
`id, tenant_id, agent_id, direction, status, outcome, caller_number, callee_number,
started_at, ended_at, duration_seconds, recording_url, transcript (jsonb), summary,
latency_ms (jsonb: {p50,p95,turns}), cost_cents, provider_snapshot (jsonb), created_at`

### call_event  (turn-level detail / tool calls / errors)
`id, tenant_id, call_id, seq, type (user|agent|tool|error), content (jsonb),
stt_ms, llm_ms, tts_ms, created_at`

### booking
`id, tenant_id, call_id, agent_id, customer_name, customer_phone, service, start_at, end_at,
status (booking_status), external_ref (calcom/google id), notes, created_at, updated_at`

### lead
`id, tenant_id, call_id, name, phone, email, intent, message, tags (jsonb), created_at`

### integration
`id, tenant_id, type (integration_type), config (jsonb), secret (encrypted), status, created_at, updated_at`
— secrets encrypted at rest (see [13](13-security-compliance.md)); never returned in API responses.

### usage_event
`id, tenant_id, call_id, provider_kind, provider, units (jsonb: {minutes|tokens|chars}),
cost_cents, created_at` — powers analytics + billing.

### (Phase 4) eval_run / eval_case
`eval_run(id, tenant_id, agent_version, started_at, passed, summary jsonb)` ·
`eval_case(id, run_id, scenario, passed, scores jsonb, transcript jsonb)`

## Conventions
- All FKs `ON DELETE CASCADE` within a tenant's aggregate where appropriate.
- `jsonb` for flexible/evolving config; promote to columns when queried often.
- Money in integer **cents** (`cost_cents`).
- Vector `DIM` fixed per deployment by the embeddings model; changing models requires reindex.
- Every list query filters by `tenant_id`; composite indexes lead with `tenant_id`.
