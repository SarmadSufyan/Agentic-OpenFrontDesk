# OpenFrontDesk — Progress Log

> Single source of truth for build progress. Updated at the end of every work session.
> Legend: ✅ done · 🚧 in progress · ⬜ not started · ⏸️ blocked/parked

**Current phase:** SaaS build — M1 (access engine) + M2 (chat widget) + M3 (automations) ✅ done → M4 (contact/personalization) next
**Last updated:** 2026-09-23
**Note:** Live voice call verified working end-to-end (Groq `openai/gpt-oss-20b`, Kokoro TTS, turn-detector baked in). Phases 0–4 built; pushed to GitHub (CI green). Now building the SaaS product layer.

---

## Milestone overview

| Phase | Name | Status | Goal |
|------|------|--------|------|
| 0 | Foundations | ✅ | Repo, docs, config, DB, provider interfaces — runnable skeleton |
| 1 | Talking agent | ✅ | A real (browser) voice call: STT → LLM → TTS |
| 2 | Useful agent | ✅ | RAG knowledge, booking, take-message, transfer, SMS |
| 3 | The product | ✅ | Multi-tenant dashboard, onboarding, call logs, analytics |
| 4 | Production-grade | 🚧 | Eval harness ✅, observability, telephony go-live, security |
| 5 | Launch | ⬜ | Live demo, README polish, first case study |

---

## Phase 0 — Foundations 🚧

**Definition of done:** `docker compose up` brings up Postgres+pgvector, Redis, and the API; `GET /health` returns healthy; models + migrations exist; provider interfaces defined with at least one implementation each; all core docs written.

- [x] Repo initialized (git, folder structure)
- [x] Packaging (`pyproject.toml`) + tooling (ruff, mypy, pytest)
- [x] `.env.example` with full provider matrix (free-stack defaults)
- [x] License (Apache-2.0), `.gitignore`
- [x] Documentation set (`docs/00` … `docs/16`) + ADRs
- [x] `progress.md` (this file)
- [x] Core config module (`ofd.core.config`) with typed settings
- [x] Structured logging (`ofd.core.logging`)
- [x] Async DB layer (`ofd.db`) + SQLAlchemy base (lazy engine — importable without a DB)
- [x] Data models (tenant, user, membership, agent, phone_number, knowledge, doc_chunk, call, call_event, booking, lead, integration, usage) — 13 tables, ORM graph validated
- [x] Pydantic schemas foundation (`health`, `common`); per-entity schemas land with their routers
- [x] FastAPI app + `/health` (liveness + `?deep=1`) + router mount point
- [x] Provider abstraction: STT / LLM / TTS / Embeddings protocols + registry
- [x] One implementation each (Groq STT, Groq + Gemini LLM, Kokoro TTS, fastembed + Gemini embeddings)
- [x] Alembic wired (async `env.py`, template with pgvector, auto-creates extension) + `scripts/init_db.py`
- [x] `docker-compose.yml` (pgvector, redis, api, kokoro, agent) + Dockerfiles + `Makefile`
- [x] Skeleton verified: all sources compile; `pytest` green (`/health` + OpenAPI); ORM mappers configure
- [x] Docker end-to-end verified on host (2026-09-21): db+redis healthy, `init_db` created schema,
      `/health` + `/health?deep=1` green. API published on **:8080** (8000 taken by another project);
      host port is now configurable via `API_HOST_PORT`.

## Phase 1 — Talking agent ✅ (code)
- [x] LiveKit worker (`ofd.agent`): `worker.py`, `providers.py`, `prompt.py`, `metrics.py`, `__main__.py`
- [x] VAD (silero, prewarmed) + turn detection (turn-detector plugin, VAD fallback)
- [x] STT → LLM → TTS chained pipeline via `AgentSession`, config-driven plugin selection
- [x] Browser test room: `GET /livekit/token` + `/test` page (livekit-client) + `/` landing
- [x] System prompt / persona builder (`build_instructions`)
- [x] Per-call latency logging (EOU + LLM ttft + TTS ttfb, p50/p95)
- [x] Unit tests: token endpoint config-guard, test page + landing served (5 tests green)
- [x] Seeded eval scenarios (`eval/scenarios/*.yaml`) — habit started for the Phase 4 harness
- [ ] **Live spoken-call verification** — pending: needs LiveKit creds + running worker + Kokoro + GROQ_API_KEY
      (see run steps below; can't be exercised without those accounts/services)

## Phase 2 — Useful agent ✅ (code)
- [x] Document ingestion (PDF/DOCX/TXT/text/URL) → chunk → embed → pgvector (`ofd/rag/*`, `services/knowledge.py`)
- [x] `search_knowledge` tool — grounded, sources tracked; returns NO_RESULTS instead of hallucinating
- [x] `book_appointment` + `check_availability` — **internal calendar** (free, no account) + optional Cal.com; read-back
- [x] `take_message` / `request_callback` (→ `capture_lead`)
- [x] `transfer_to_human` (real transfer = Phase 4)
- [x] `send_sms_confirmation` (no-op default; Twilio optional)
- [x] Per-tenant agent config loaded at call start (worker resolves tenant via participant metadata)
- [x] Knowledge management API: `POST /knowledge/{text,url,file}`, `GET /knowledge`, `/search`, reindex, delete
- [x] Demo seed (`scripts/seed_demo.py`) — dental clinic tenant + agent + knowledge
- [x] `CALENDAR_BACKEND` config (internal|calcom); tenant resolver dep (`?tenant=` until auth)
- [x] Unit tests green (9 total: health, token, pages, chunker); services/RAG import-checked; 11 API routes registered
- [ ] **Live verification** pending: ingest a doc (needs Postgres + fastembed) and complete a spoken
      booking call (needs LiveKit + worker). Steps in the summary.

## Phase 3 — The product ✅ (verified live 2026-09-21)
- [x] Auth: `/auth/signup`, `/login`, `/refresh`, `/me` — bcrypt (direct) + JWT access/refresh
- [x] Membership-enforced multi-tenancy + roles (`get_context`, `require_roles`); isolation verified
- [x] Workspace API: `GET/PATCH /tenants/current`, `GET/PUT /agents/current`
- [x] Knowledge API now auth-aware (token → tenant), keeps dev `?tenant=` fallback
- [x] Call persistence (`services/calls.py`) + read APIs: `/calls`, `/calls/{id}`
- [x] `/bookings`, `/leads`, `/analytics/overview`
- [x] Simple dashboard served at **/app** (login, overview, calls, bookings, leads, knowledge, agent)
      — vanilla JS single page for now; Next.js swap deferred per user preference
- [x] Worker wires best-effort call logging (start/finalize + transcript + latency, attaches call_id)
- [x] Seed adds a demo login (`demo@openfrontdesk.local` / `demodemo12`) + sample booking/lead/call
- [x] **Verified live in Docker:** login, /me, workspace, analytics, calls/bookings/leads, dashboard 200,
      401 guard, signup → isolated new tenant (all zeros)

## Phase 4 — Production-grade 🚧
- [x] Eval harness: scenario loader (`eval/schema.py`), deterministic scorers (`eval/scorers.py`),
      text-mode runner with synthetic caller + real tools (`eval/runner.py`), CLI (`python -m eval`)
- [x] Scenario suite (booking, faq-hours, unknown-price, transfer-upset) + unit tests (4 passing)
- [x] CI regression gate (`.github/workflows/ci.yml`: ruff + pytest + `eval --validate`)
- [x] Observability: `/metrics` (Prometheus text) + HTTP request counters + structured logs
- [x] Per-tenant rate limiting / quotas (Redis fixed-window, `services/quota.py` + `rate_limit` dep on writes)
- [x] Security: PII redaction in logs (email/phone), security headers (nosniff / DENY / no-referrer)
- [x] Non-blocking ingestion (create doc → background embed job) + dashboard call-detail view + audit tab
- [x] Audit log (tenant/agent/knowledge changes, `GET /audit`) + recording-consent config (gated, off by default)
- [ ] Full eval RUN in CI — needs an LLM key + seeded DB (framework ready: `python -m eval --run`)
- [ ] OpenTelemetry traces + Langfuse LLM traces (config-gated; not wired yet)
- [ ] Provider failover + minutes/spend caps (rate limiter in place; spend caps TODO)
- [ ] Telephony go-live (Telnyx/Twilio SIP → LiveKit) — needs a telephony account

## SaaS product ("OpenFrontDesk Cloud") — M1–M6
Repositioned: train an AI on your docs, deploy as voice agent + embeddable web chat widget + n8n/Zapier
automations. Free model: cap concurrent voice + waitlist + email allowlist (accounts/knowledge/text/
widget unlimited; open signups). Decisions (2026-09-23): frontend = Next.js + shadcn/ui; flagship =
chat widget first then automations.

- [x] **M1 — Access engine:** Redis concurrency cap + FIFO waitlist + priority allowlist
      (`services/access.py`), `access_allowlist` table, `/voice/{acquire,heartbeat,release,status}`
      (mints the LiveKit token only when a slot is granted), `/admin/*` (allowlist + live sessions,
      gated by `ADMIN_EMAILS`). Verified: cap=3 grants 3 + queues the 4th, release promotes FIFO,
      allowlist bypasses a full cap; endpoints + admin auth confirmed.
- [x] **M2 — Embeddable chat widget:** grounded text-chat brain (`services/chat.py`, OpenAI-compatible
      LLM via httpx + the same tools), public per-tenant endpoints (`/widget.js`, `/widget/{slug}/config`,
      `/widget/{slug}/chat`), a `/widget-demo` page, open CORS, rate-limited. Verified: grounded $250
      answer with sources; refuses to invent; leads/bookings flow to the dashboard.
- [x] **M3 — Automations:** signed outbound webhooks (`lead.created`, `booking.created`,
      `call.completed`, `knowledge.ready`) with HMAC-SHA256, retries/backoff, delivery log, auto-disable,
      SSRF guard (checked on save and on every send), dispatched only after the DB transaction commits;
      hashed workspace API keys + public `/v1` API (me, chat, knowledge search, leads, availability,
      bookings, calls); dashboard Integrations tab; 3 n8n templates (leads to Sheets+Slack, call
      transcript email, WhatsApp answered by the agent); optional n8n compose profile;
      docs/17-automations.md. Verified: 46 tests; HTTP e2e (SSRF 422, key lifecycle, every /v1
      endpoint, revoke gives 401, audit entries); in-container signed delivery on commit and none on
      rollback; template signature node run on real n8n 2.40 (valid passes, tampered/stale rejected,
      API container to n8n delivery 200).
- [ ] **M4 — Contact/personalization:** contact form + scheduling link + admin inbox.
- [ ] **M5 — Modern frontend (Next.js + shadcn/ui):** landing, auth, onboarding, dashboard, test console.
- [ ] **M6 — Deploy + launch:** Vercel (frontend) + VPS (backend) + docs + live demo.

## Phase 5 — Launch ⬜
- [ ] Hosted live demo (browser + one phone number)
- [ ] README demo GIF + one-command quickstart
- [ ] Docs site
- [ ] Show HN / r/selfhosted / Product Hunt
- [ ] First case study with metrics

---

## Worklog

### 2026-09-19
- Initialized repository, monorepo folder structure, git (branch `main`).
- Added packaging (`pyproject.toml`), `.env.example` (free-stack defaults), Apache-2.0 license, `.gitignore`.
- Wrote the full documentation set (`docs/00`–`16` + 4 ADRs).
- Built the Phase 0 backend skeleton: config, logging, exceptions, security, async DB (lazy engine),
  13 ORM models, provider abstraction + registry + one impl per capability, FastAPI app with `/health`,
  Alembic (async) + `init_db.py`, Docker Compose + Dockerfiles + Makefile.
- **Verified locally:** `compileall` clean; created `.venv`; `pytest` → 2 passed (`/health` liveness +
  OpenAPI); `configure_mappers()` OK across all 13 tables; provider imports OK.
- Not done: Docker end-to-end (Docker Desktop engine offline in this session) and the first Alembic
  autogenerate (needs a running DB). Both are one-liners once Docker is up — see docs/11-deployment.md.
- No git commit made yet (awaiting go-ahead).

### 2026-09-20
- Built Phase 1 (talking agent): LiveKit worker with VAD + turn detection + chained STT→LLM→TTS,
  config-driven plugin selection (`ofd/agent/providers.py`), persona prompt, latency tracker.
- Added `GET /livekit/token`, a same-origin `/test` browser call page, and a `/` landing.
- Updated deps: `livekit-api` (core, for tokens) + agent extra (livekit-agents + silero/groq/openai/
  turn-detector plugins).
- Seeded `eval/scenarios/` with two scenarios + eval README.
- **Verified:** `compileall` clean; `pytest` → 5 passed (health + token guard + pages).
- Not exercised here: a real spoken call (needs LiveKit Cloud creds, GROQ_API_KEY, running Kokoro +
  `ofd-agent` worker). Run steps are in the summary / docs/11-deployment.md.

### 2026-09-20 (Phase 2)
- RAG layer: `rag/chunk.py` (tested), `rag/parse.py` (pdf/docx/txt/url), `rag/retrieve.py` (pgvector cosine).
- Services: `knowledge` (ingest/reindex/delete/search), `booking` (internal calendar + optional Cal.com),
  `leads`, `tenants`; `telephony/sms` (noop/Twilio); `services/calcom.py` client.
- Agent tools (`agent/frontdesk.py`): search_knowledge, check_availability, book_appointment,
  take_message, request_callback, transfer_to_human, send_sms_confirmation. Worker now resolves the
  tenant/agent per call and builds tool-aware, grounded instructions.
- API: knowledge router (text/url/file/list/search/reindex/delete); token endpoint attaches tenant
  metadata; demo seed script (dental clinic); `CALENDAR_BACKEND` config.
- **Verified:** compileall clean; `pytest` 9 passed; services/RAG import OK; 11 routes registered.
- Not exercised here (no running Postgres/LiveKit): live ingestion + a spoken booking call.

### 2026-09-21 (Phase 3 build + verify)
- Added auth (bcrypt + JWT), membership-enforced tenancy + roles, workspace/agent APIs, calls persistence
  + read APIs, bookings/leads reads, analytics overview, and a simple `/app` dashboard.
- Seed now creates a demo login + sample records; worker persists calls best-effort.
- **Two fixes worth remembering:**
  1. `Dockerfile.api` was installing `.[providers,rag]`, which pulled `google-generativeai` → pip
     backtracked forever on `grpcio-status`. The API doesn't need LLM/STT SDKs → slimmed to `.[rag]`.
     (The agent worker image keeps `[providers]`.)
  2. `passlib[bcrypt]` is unmaintained and breaks with bcrypt 4.x (`no attribute '__about__'` + a
     72-byte error). Replaced passlib with the `bcrypt` library used directly in `core/security.py`.
- **Verified live** in Docker on the user's machine (see Phase 3 checklist).

**Next (Phase 4):** eval/simulation harness + CI gate; observability (OTel + Langfuse + metrics);
provider failover + cost caps; telephony go-live (Telnyx/Twilio SIP); security pass. (Voice keys from the
user unlock live-call testing of Phases 1–2 at any time.)

### 2026-09-21 (Phase 4, part 1 — eval harness)
- Built the eval/simulation harness: `eval/schema.py` (YAML scenario loader), `eval/scorers.py`
  (deterministic scorers: task_success, no_unsupported_price, captured_contact, latency_ok),
  `eval/runner.py` (text-mode: synthetic caller LLM ↔ agent brain + real tools, via our provider
  abstraction), and `python -m eval` CLI (`--validate` / `--run`).
- Scenario suite: booking-basic, faq-hours, faq-unknown-price, transfer-upset.
- Added `.github/workflows/ci.yml` (ruff + pytest + `eval --validate`) and updated the Field Guide.
- **Verified:** `compileall` clean; `pytest tests/test_eval.py` → 4 passed; `python -m eval --validate`
  lists all 4 scenarios. Full `--run` needs `GROQ_API_KEY` + seeded DB (framework ready).
- Also added `bcrypt`, `pyyaml` to deps; `[eval]` extra.

### 2026-09-21 (Phase 4, part 2 — observability, quotas, security)
- Observability: `ofd/core/metrics.py` (dependency-free Prometheus registry) + `/metrics` endpoint +
  HTTP request counters via middleware.
- Quotas: `ofd/services/quota.py` (Redis fixed-window limiter, fail-open) + `rate_limit` dependency
  applied to knowledge write endpoints; `TooManyRequests` (429).
- Security: PII redaction structlog processor (`_redact` — email + 10–15 digit phone runs, keeps
  dates/versions/ports) and security headers (nosniff / X-Frame-Options DENY / Referrer-Policy).
- Config: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MIN`, `SECURITY_HEADERS`, `RECORDING_ENABLED`.
- **Verified live:** `/metrics` shows counters; headers present on `/health`; limiter allows 3 then
  blocks (limit=3); redaction + metrics unit tests pass (8 total with eval).

**Remaining in Phase 4 (needs accounts/keys):** wire the full `eval --run` into CI (LLM key), optional
OTel/Langfuse, and telephony go-live (Telnyx/Twilio account + number).

### 2026-09-21 (Phase 4, part 3 — robustness bundle)
- Non-blocking ingestion: split `create_doc` from `run_ingestion`; knowledge write endpoints create +
  commit the doc (status `pending`, HTTP 202) then run embedding via a FastAPI BackgroundTask
  (`ingest_job`). Fixed a real ordering bug — the task raced the request's deferred commit and saw no
  row (`ingest_job_missing_doc`); now the doc is committed in its own session before scheduling.
- Audit log: `audit_log` table + `services/audit.py`; recorded on tenant/agent updates and knowledge
  add/delete; `GET /audit` (owner/admin) + dashboard Audit tab.
- Dashboard: call-detail view (transcript + outcome + latency).
- Recording-consent config plumbing in the worker (gated by `RECORDING_ENABLED`, off by default).
- **Verified live:** POST /knowledge/text → `pending` (202) → `ready` (background), then searchable;
  audit shows `tenant.update` + `knowledge.add`; call detail returns transcript; dashboard serves.
- Note: `init_db` re-run to create the new `audit_log` table.

### 2026-09-21 (user testing — Phase 0)
- Started Docker Desktop (engine was off). Built the API image (~284s, one-time).
- Port 8000 clash with the user's other running project (`corepartners_api`); made the API host port
  configurable (`API_HOST_PORT`, docker-compose) and set it to **8080** for this machine.
- Verified live: db+redis healthy, `scripts/init_db.py` OK, `/health` + `/health?deep=1` green.
- Phase 0 acceptance met on the user's host. Next test: Phase 2A RAG (seed + search), no API keys.

### 2026-09-23 (SaaS M3 — automations)
- Docker builds now cache the dependency layer (install against a stub package, then copy `src`); the
  agent image also bakes the Silero and turn-detector model files. Source-only rebuilds of the API
  dropped from minutes to seconds.
- Webhooks: `webhook_endpoint` / `webhook_delivery` tables, `services/webhooks.py` (HMAC signing,
  SSRF guard, retries with backoff, delivery log, auto-disable). Events are queued on the DB session
  and dispatched from an `after_commit` hook, so a rolled-back request never announces data that does
  not exist. First version used `after_rollback` to drop queued events; a unit test showed it does not
  fire for a rollback that never touched the DB, so it now uses `after_soft_rollback` (ignoring
  savepoints).
- API keys: `api_key` table, SHA-256 hashed, shown once, `last_used_at` throttled, revocable;
  `get_api_context` dependency with a per-workspace rate limit.
- Routers: `/integrations/*` (owner/admin; audit-logged) and the public `/v1` API. Dashboard gained an
  Integrations tab (show-once secrets, test button, delivery log, key management).
- n8n: three templates + README; `n8n` compose service under the `automation` profile
  (`NODE_FUNCTION_ALLOW_BUILTIN=crypto` for the signature Code node).
- **Verified live:** 46 tests pass; SSRF rejects loopback and the cloud metadata IP (422); unknown event
  rejected; list views hide secrets; key lifecycle incl. Bearer form and revoke giving 401; every `/v1`
  endpoint (chat answered "$90" for a cleaning, grounded); a public endpoint delivery returned 405 and
  was correctly not retried; in-container receiver got `lead.created` + `booking.created` with valid
  signatures and nothing for the rolled-back lead; on n8n 2.40 the template's Code node accepted a valid
  signature (non-ASCII payload), rejected tampered and stale ones, and a real API-to-n8n delivery
  returned 200. Agent image rebuilt and re-registered with LiveKit.
- Note: `init_db` re-run to create the three new tables.
