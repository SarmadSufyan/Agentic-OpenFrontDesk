# 16 — Roadmap & Milestones

Phased, milestone-by-milestone. Live status is tracked in [`/progress.md`](../progress.md); this doc
holds scope + acceptance criteria per phase.

## Phase 0 — Foundations 🚧
**Scope:** repo, docs, packaging, config, logging, async DB, data models, Pydantic schemas, FastAPI app
with `/health`, provider abstraction + one impl each, Alembic, Docker Compose.
**Acceptance:** `docker compose up db redis` + `ofd-api` → `GET /health` green; migrations create schema;
`ruff`/`mypy` clean; docs complete.

## Phase 1 — Talking agent
**Scope:** LiveKit worker; VAD + turn detection; STT→LLM→TTS chained pipeline; `/livekit/token`; a
browser page to talk to the agent (free); latency logging.
**Acceptance:** you can hold a real spoken conversation in the browser; per-turn latency logged;
p95 within budget on the free stack.

## Phase 2 — Useful agent
**Scope:** document ingestion (PDF/DOCX/URL) → pgvector; `search_knowledge` (grounded + citations);
`book_appointment` via Cal.com (+ read-back); `take_message`/`capture_lead`; `transfer`/`callback`;
`send_sms`; per-tenant config at call start.
**Acceptance:** agent books a real Cal.com appointment and answers only from uploaded docs (refuses when
unknown) in a live browser call; artifacts persisted.

## Phase 3 — The product
**Scope:** auth + tenants + memberships; onboarding wizard API; Next.js dashboard (onboarding, test
console, calls, bookings, analytics); call storage + transcripts + recordings; analytics endpoints.
**Acceptance:** a new user signs up, onboards a business, teaches it, tests in-browser, and reviews the
call — all through the UI. Multi-tenant isolation verified.

## Phase 4 — Production-grade
**Scope:** eval harness + scenario suite + scorers + CI gate; observability (OTel + Langfuse + metrics);
provider failover + cost caps; telephony go-live (Telnyx/Twilio SIP); security pass (redaction, consent,
audit, quotas).
**Acceptance:** eval suite runs in CI and blocks regressions; a real phone number takes a live call;
security checklist ([13](13-security-compliance.md)) complete.

## Phase 5 — Launch
**Scope:** hosted live demo (browser + one number); README demo GIF + one-command quickstart; docs site;
Show HN / r/selfhosted / Product Hunt; first case study with metrics.
**Acceptance:** anyone can call the demo or self-host in minutes; a written case study with real numbers.

## Guiding constraints
- Backend/architecture first; UI stays simple until the system works.
- Free stack by default; premium is a config swap.
- Every phase ends with `progress.md` updated and a working, demoable increment.
