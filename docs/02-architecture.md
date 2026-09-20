# 02 — System Architecture

This is the backbone document. It defines components, boundaries, and the two critical flows
(**a live call** and **knowledge ingestion**), plus deployment topology and scaling.

## 1. Design principles
1. **Provider abstraction is sacred.** Every external AI/telephony service sits behind an interface in
   `ofd.providers` / `ofd.telephony`. Swapping Groq↔Deepgram or Kokoro↔Cartesia is config, not code.
   See [ADR-0002](adr/0002-provider-abstraction.md).
2. **Tenant isolation everywhere.** Every row carries `tenant_id`; every query is scoped. [09](09-multi-tenancy-auth.md).
3. **Stream everything.** Perceived latency is the product; never wait for a full response when a
   partial one can start the next stage. [04](04-voice-pipeline.md).
4. **Fail safe, never silent.** Any pipeline failure degrades to voicemail/human/callback and is logged.
5. **Stateless services, stateful stores.** API and agent workers are horizontally scalable; state lives
   in Postgres/Redis/object storage.
6. **The agent and the API share one codebase** (`src/ofd`) but run as **separate processes**.

## 2. Components (logical)

```
┌──────────────┐     ┌───────────────────────────────────────────────┐
│  Dashboard   │◄───►│  API service  (FastAPI, src/ofd/api)           │
│  (Next.js)   │ REST│  auth · tenants · knowledge · calls · bookings │
└──────────────┘  WS │  analytics · LiveKit token minting · webhooks  │
                     └───────────────┬───────────────────────────────┘
                                     │ shared models / services / providers
                     ┌───────────────┴───────────────────────────────┐
                     │  Agent worker (LiveKit Agents, src/ofd/agent)  │
   Caller ──► LiveKit│  VAD → turn-detect → STT → LLM(+RAG+tools)→TTS │
 (phone/browser) SFU │  tools call back into ofd.services             │
                     └───────────────┬───────────────────────────────┘
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     │            Shared infrastructure & stores                       │
     │  Postgres + pgvector   Redis (cache/queue)   Object storage     │
     └────────────────────────────────────────────────────────────────┘

  External services (behind interfaces):
   STT/LLM/TTS/Embeddings providers · LiveKit media · Telnyx/Twilio SIP+SMS · Cal.com/Google Calendar
```

## 3. Processes (deployable units)
| Process | Package | Scales on | Notes |
|---|---|---|---|
| `ofd-api` | `ofd.api` | HTTP/WS load | Stateless; N replicas behind nginx |
| `ofd-agent` | `ofd.agent` | concurrent calls | LiveKit worker pool; one job per call |
| `ofd-worker` (later) | `ofd.services.jobs` | background jobs | ingestion, SMS, outbound; Redis queue |
| Postgres+pgvector | — | data | primary store + vectors |
| Redis | — | cache/queue | sessions, rate limits, job queue |
| Kokoro-FastAPI (free TTS) | external | TTS load | self-hosted on VPS (CPU) |

## 4. Flow A — inbound call lifecycle (the hot path)

```
1. Caller dials number (or opens browser test) 
2. Telephony (Telnyx/Twilio SIP) → LiveKit room  |  browser → LiveKit room directly
3. LiveKit dispatches the job to an available ofd-agent worker
4. Worker loads tenant + agent config (by dialed number / room metadata) from cache→DB
5. Greeting (TTS) plays; VAD + turn detection start listening
6. Loop per turn:
     audio → STT (streaming, partials)
           → LLM with system prompt + tools + conversation state
                • if tool call: search_knowledge / book_appointment / take_message / transfer / send_sms
                • tools execute via ofd.services (DB, Cal.com, SMS)
           → response text streamed sentence-by-sentence → TTS → caller
7. On end/hangup: persist call (recording URL, transcript, outcome, latency, cost) via API/services
8. Post-call: SMS confirmation, CRM webhook, alerts (enqueued to Redis)
```

Latency budget target (chained, free stack): **p50 < 700ms, p95 < 1100ms** end of caller speech →
first audio back. TTS (Kokoro CPU) is the main variable; premium (Cartesia) pushes p50 toward ~400ms.

## 5. Flow B — knowledge ingestion (async)

```
Upload/URL → API stores file (object storage) + creates knowledge_doc(status=pending)
          → enqueue ingestion job (Redis)
worker: parse (pypdf/python-docx/BeautifulSoup) → clean → chunk (token-aware, overlap)
      → embed (fastembed/Gemini) → upsert doc_chunks(embedding vector) in pgvector
      → knowledge_doc(status=ready); dashboard shows ✅
```
Retrieval at call time: embed the caller's question → pgvector similarity (+ optional keyword hybrid)
→ top-k chunks → passed to LLM as grounded context with source ids for citation. [05](05-rag.md).

## 6. Deployment topology — FREE stack (default)

```
 Vercel (free)            Hostinger VPS (owned)                   Managed free tiers
 ┌───────────┐   HTTPS    ┌──────────────────────────────────┐   ┌──────────────────┐
 │ Dashboard │───────────►│ nginx → ofd-api (uvicorn)         │   │ LiveKit Cloud    │
 │ (Next.js) │            │ ofd-agent (LiveKit worker)        │──►│  Build (free)    │
 └───────────┘            │ Postgres+pgvector · Redis         │   │ Groq (STT+LLM)   │
                          │ Kokoro-FastAPI (TTS, CPU)         │──►│ Gemini (LLM/embed)│
                          │ object storage (local dir)        │   └──────────────────┘
                          └──────────────────────────────────┘
   Telephony: NONE for testing (browser mic). Telnyx number added per client at go-live.
   New monthly cost ≈ $0 (VPS already owned). See 12-costing.md.
```

Everything runs via `docker-compose.yml`. Kokoro runs as its own container (OpenAI-compatible API).

## 7. Deployment topology — PREMIUM / scale (client-funded)
Swap providers via env: Deepgram STT, Cartesia TTS, Claude/Gemini-paid LLM, LiveKit Ship or self-hosted
SFU, Telnyx/Twilio SIP for real phone numbers. Add more `ofd-agent` replicas for concurrency, move
Postgres to a managed instance, object storage to S3/MinIO. No application code changes.

## 8. Scaling path
- **Concurrency = number of simultaneous calls** → scale `ofd-agent` replicas (1 job ≈ 1 call).
- API is stateless → scale replicas behind nginx.
- Postgres: start single node; add read replicas + connection pooler (pgbouncer) later.
- Redis: single node → cluster if needed.
- Rate limits: free provider tiers cap concurrency → per-tenant premium upgrade handles busy clients.

## 9. Cross-cutting concerns
- **Config:** one typed settings object (`ofd.core.config`), env-driven. [03](03-backend.md).
- **Auth & tenancy:** JWT + `tenant_id` scoping + row checks. [09](09-multi-tenancy-auth.md).
- **Observability:** structured logs, OpenTelemetry traces, Langfuse LLM traces, metrics. [14](14-observability.md).
- **Security/compliance:** PII encryption, recording consent, HIPAA self-host path. [13](13-security-compliance.md).
- **Testing:** unit + integration + the voice eval harness. [10](10-eval-harness.md).

## 10. Key decisions (see `adr/`)
- LiveKit Agents for orchestration ([0001](adr/0001-livekit-agents.md)).
- Provider abstraction layer ([0002](adr/0002-provider-abstraction.md)).
- Postgres + pgvector as the single store (no separate vector DB) ([0003](adr/0003-postgres-pgvector.md)).
- Chained pipeline as default over speech-to-speech ([0004](adr/0004-chained-pipeline.md)).
