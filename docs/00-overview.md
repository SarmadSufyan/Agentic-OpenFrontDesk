# 00 — Overview

## What OpenFrontDesk is
An open-source, self-hostable **AI voice receptionist** for small and medium businesses. It answers
inbound phone calls 24/7 and:

- answers questions from the business's **own** documents (grounded, cited),
- **books / reschedules / cancels** appointments against a real calendar,
- **captures leads** and takes messages,
- **transfers to a human** or arranges a callback when it should,
- sends an **SMS** follow-up/confirmation after the call.

## The problem
- SMBs miss **30–40%** of calls → direct lost revenue. Human receptionists are costly and 9–5.
- Commercial voice-AI SaaS (Vapi/Retell/Bland) is **closed** and **expensive** — advertised
  per-minute rates balloon 3–5× in practice; HIPAA tiers can be ~$1k/mo.
- Existing OSS receptionists are **thin demos**: single-tenant, one hard-wired provider, no tests,
  no real dashboard, no booking reliability.

## The gap we fill (positioning)
> The **production-grade middle** between a hobby GitHub repo and a $500–1,000/mo closed SaaS.

Differentiators:
1. **Provider-agnostic** — free stack (Groq/Gemini/Kokoro) ↔ premium (Deepgram/Cartesia/Claude) by config.
2. **Eval/simulation harness** — automated, CI-gated call testing (the "production" soul).
3. **Multi-tenant** — real SaaS data model from day one.
4. **Grounded RAG** — answers from the client's docs, with citations; refuses to hallucinate.
5. **Free to demo** — browser-mic testing; telephony only at go-live.

## Goals
- A genuinely **usable, live** product (not a demo) that anyone can self-host in minutes.
- A **portfolio flagship** demonstrating: real-time voice, RAG, agentic tool-use, multi-tenancy,
  evals, observability, and DevOps.
- A base you can **resell/deploy per client** (Upwork / agencies).

## Non-goals (for now)
- Not a general no-code agent builder (that's a v2 flow builder).
- Not fine-tuning/training custom speech or language models (we use RAG + hosted/self-hosted models).
- Not an omnichannel helpdesk (voice-first; chat/web widget can come later).

## Who it's for
- **End users:** appointment-driven SMBs — clinics/dental, salons/spas, home services, law firms,
  real estate, restaurants.
- **Operators:** freelancers/agencies who deploy and manage it per client.

## Success metrics
- Calls handled autonomously, bookings created, deflection %, missed-call recovery, avg latency
  (p50/p95), cost per call. See [14-observability](14-observability.md).

## Map of the docs
`01` product/UX · `02` architecture · `03` backend · `04` voice pipeline · `05` RAG · `06` data model ·
`07` providers · `08` telephony · `09` multi-tenancy/auth · `10` eval harness · `11` deployment ·
`12` costing · `13` security · `14` observability · `15` API reference · `16` roadmap · `adr/` decisions.
