# 03 — Backend Design

The backend is the priority of this project. Python 3.11+, FastAPI, async SQLAlchemy 2.0. The API and
the voice agent import the **same** package (`src/ofd`) so business logic is written once.

## 1. Package layout (`src/ofd`)

```
ofd/
├── core/            # config, logging, security (JWT/hashing), exceptions, constants
├── db/              # async engine, session, Base, unit-of-work helpers
├── models/          # SQLAlchemy ORM models (one file per aggregate)
├── schemas/         # Pydantic request/response models (API contract)
├── api/             # FastAPI app + routers (thin HTTP layer)
│   ├── deps.py      # dependencies: db session, current user/tenant, pagination
│   └── routers/     # health, auth, tenants, agents, knowledge, calls, bookings, livekit
├── services/        # business logic (framework-agnostic; called by API AND agent)
│   ├── tenants.py   booking.py  knowledge.py  calls.py  leads.py  analytics.py
│   └── jobs/        # background job handlers (ingestion, sms, outbound)
├── providers/       # STT / LLM / TTS / Embeddings abstraction + implementations
│   ├── base.py      registry.py
│   ├── stt/  llm/  tts/    # one module per implementation
├── rag/             # ingestion (parse/chunk/embed) + retrieval
├── agent/           # LiveKit worker + tool definitions (thin; delegates to services)
│   └── tools/
└── telephony/       # SIP/number provisioning + SMS abstraction
```

## 2. Layering rules (dependency direction)

```
api  ─┐
       ├─►  services  ─►  models / db / providers / rag / telephony  ─►  core
agent ─┘
```
- **Routers are thin:** validate input (Pydantic) → call a service → serialize output. No business logic.
- **Services are the brain:** transactions, orchestration, invariants. Reusable by API and agent alike.
- **Providers/telephony are replaceable edges.** Services depend on the *interfaces*, never on a vendor.
- `core` depends on nothing internal.

## 3. Request lifecycle (API)
1. nginx → uvicorn → FastAPI.
2. Middleware: request id, structured logging, CORS, timing.
3. Dependencies (`api/deps.py`): open async DB session, resolve current user + tenant from JWT.
4. Router handler → service call (inside a transaction / unit of work).
5. Service returns domain objects → Pydantic response schema → JSON.
6. Errors → mapped by a central exception handler to typed JSON problem responses.

## 4. Configuration
- Single `Settings` object (`ofd.core.config`, `pydantic-settings`), loaded from env/`.env`.
- Provider selection keys (`STT_PROVIDER`, `LLM_PROVIDER`, …) drive the registry factories.
- `DATABASE_URL` auto-assembled from `POSTGRES_*` if not set.
- Import once: `from ofd.core.config import settings`.

## 5. Database & migrations
- Async engine (`asyncpg`), `async_sessionmaker`, `AsyncSession` per request/scope.
- `Base` = `DeclarativeBase` with shared mixins: `id (UUID)`, `created_at`, `updated_at`, and (where
  tenant-owned) `tenant_id` + index.
- **Alembic** for migrations; `pgvector` extension enabled in the first migration.
- Vector columns via `pgvector.sqlalchemy.Vector(dim)`.

## 6. Background jobs
- Redis-backed queue (start simple; `arq` or a thin custom consumer). Jobs: **ingestion**, **SMS send**,
  **outbound reminders/callbacks**, **CRM webhooks**, **post-call processing**.
- Jobs are just service calls with retries (`tenacity`) + idempotency keys.
- Keeps the hot call path free of slow I/O.

## 7. Error handling & resilience
- Typed exceptions in `core.exceptions` (`NotFound`, `Forbidden`, `TenantMismatch`, `ProviderError`, …).
- Provider calls wrapped with timeouts + retries + circuit-breaker semantics; on exhaustion the agent
  degrades safely (voicemail/human) and records the failure.
- Every external call is traced with latency + cost attributes.

## 8. Security
- Passwords hashed with bcrypt (`passlib`); JWT access tokens (`pyjwt`), short-lived + refresh.
- Tenant scoping enforced in a dependency AND re-checked in services (defense in depth).
- Secrets only from env; never logged. PII redaction in logs. See [13](13-security-compliance.md).

## 9. API surface (v1)
`/health` · `/auth/*` · `/tenants/*` · `/agents/*` · `/knowledge/*` (upload/list/reindex) ·
`/calls/*` · `/bookings/*` · `/leads/*` · `/analytics/*` · `/livekit/token` · `/webhooks/*`.
Full contract in [15-api-reference](15-api-reference.md); live OpenAPI at `/docs`.

## 10. Testing
- **Unit:** services + providers (mocked edges).
- **Integration:** API against a real ephemeral Postgres (docker) + fake providers.
- **Voice eval harness:** scenario-based simulated calls with scorers, run in CI. [10](10-eval-harness.md).
- Tooling: `pytest` (+`pytest-asyncio`), `ruff`, `mypy`.

## 11. Conventions
- Type hints everywhere; `mypy` clean. `ruff` for lint+format.
- UUID primary keys. Timezone-aware UTC timestamps. Enums for statuses.
- Money as integer minor units (cents) or `Numeric`; never float.
- One aggregate per model file; services own cross-aggregate transactions.
