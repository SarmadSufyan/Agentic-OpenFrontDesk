# 13 — Security & Compliance

Calls contain PII (names, numbers, health/legal context). Treating this seriously is both right and a
market advantage (undercuts closed SaaS HIPAA tiers via self-hosting).

> **Implemented (Phase 4):** bcrypt password hashing, JWT auth, membership-enforced tenant isolation,
> PII redaction in logs (emails + phone numbers), security headers (nosniff / X-Frame-Options DENY /
> Referrer-Policy), and per-tenant rate limiting (Redis). Recording consent, audit log, and secret
> encryption-at-rest are still planned.

## 1. AuthN/Z
- Bcrypt password hashing; short-lived JWT + refresh rotation.
- Tenant isolation enforced in a dependency **and** re-checked in services (`TenantMismatch`).
- Role-based permissions ([09](09-multi-tenancy-auth.md)). LiveKit tokens: server-minted, per-room, short TTL.

## 2. Secrets
- All secrets from env; never logged, never in API responses.
- Integration credentials (Cal.com/Twilio/OAuth) **encrypted at rest** (app-level envelope encryption
  with a key from env/KMS). Rotatable.

## 3. PII handling
- Encrypt sensitive columns / recordings at rest; TLS in transit everywhere.
- **Log redaction:** phone numbers, emails, names scrubbed from logs (allow-list logging).
- Data retention policy per tenant: auto-delete recordings/transcripts after N days (configurable).
- Data export + delete endpoints (GDPR/CCPA "right to be forgotten").

## 4. Call recording & consent
- Recording is **opt-in per tenant**; an announced-consent line can play at call start
  (one/two-party consent varies by region — configurable). Consent state stored on the call.

## 5. Provider data policy (important)
- Free Groq/Gemini tiers may use data to improve their products → acceptable for demos/non-sensitive.
- For sensitive/paying clients: switch that tenant to **paid tiers (no training on data)** or **fully
  self-hosted** models (faster-whisper + Kokoro + Ollama) so no third party sees the data.
- **HIPAA-ready path:** full self-host on the client's own infra + BAAs with any remaining vendors +
  encryption + audit logs. This is a premium offering.

## 6. Prompt-injection / poisoned knowledge
- Retrieved document text is treated as **data, not instructions** — wrapped as quoted context; the agent
  never executes instructions found in uploaded docs or caller input.
- Tool calls validate arguments and are tenant-scoped; no tool can act cross-tenant.

## 7. Abuse & rate limiting
- Per-tenant quotas (minutes, uploads, RPM) in Redis. Max call duration + turn caps (runaway/cost guard).
- Upload size/type validation; malware scanning hook for uploads (later).

## 8. Auditability
- `call_event` + `usage_event` + integration change logs form an audit trail.
- Every AI answer stores its retrieved sources → answers are explainable after the fact.

## 9. Threat model (summary)
| Threat | Mitigation |
|---|---|
| Cross-tenant data access | `tenant_id` scoping (dep + service), optional RLS |
| Leaked secrets | env-only, encryption at rest, redaction |
| Prompt injection via docs/callers | data-not-instructions, tool arg validation |
| PII exposure in logs | redaction, retention limits |
| Cost/DoS via long/looping calls | duration/turn caps, quotas |
| Vendor data usage | per-tenant paid/self-host toggle |
