# 14 — Observability

If we can't see it, we can't call it production-grade. Three pillars: **logs, traces, metrics**, plus
**per-call telemetry** and **LLM tracing**.

> **Implemented (Phase 4):** structured logs (with PII redaction) and `/metrics` in Prometheus text
> format — HTTP request counters (`ofd_http_requests_total{method,status}`), `ofd_uptime_seconds`,
> `ofd_info{version}`. OpenTelemetry traces and Langfuse LLM tracing are config-gated and not wired yet.

## 1. Structured logging
- `structlog`; JSON in prod (`LOG_JSON=true`), pretty in dev.
- Every log line carries `request_id` / `call_id` / `tenant_id` where relevant.
- PII redacted ([13](13-security-compliance.md)).

## 2. Tracing
- OpenTelemetry spans across API → services → providers. A call is one trace; each turn a span with
  child spans for STT/LLM/TTS/tool calls (latency + cost attributes).
- Optional OTLP export (`OTEL_EXPORTER_OTLP_ENDPOINT`).

## 3. LLM tracing
- Langfuse (optional) captures prompts, completions, tool calls, tokens, cost per call → debugging +
  quality review. Sensitive data respected per tenant policy.

## 4. Per-call telemetry (stored)
On each `call`: outcome, duration, per-turn `stt_ms/llm_ms/tts_ms`, p50/p95, tokens, `cost_cents`,
provider snapshot, tool trace, transcript, retrieved sources. Powers analytics + eval + billing.

## 5. Metrics (dashboards)
| Metric | Why |
|---|---|
| Calls handled / day | volume |
| Bookings created | core value |
| Deflection % (handled w/o human) | automation rate |
| Missed-call recovery | revenue story |
| Avg/p95 latency (STT/LLM/TTS) | UX quality |
| Cost per call / minutes used | economics |
| Error/fallback rate | reliability |
| Grounding score (from evals) | trust |

## 6. Health & alerts
- `/health` (liveness), `/health?deep=1` (DB+Redis). Uptime monitor on the API.
- Alerts (Slack/email) on error-rate spikes, provider failures, quota breaches, failed ingestions.

## 7. Cost observability
- `usage_event` rows per provider per call → per-tenant cost rollups → billing + cost caps ([12](12-costing.md)).
