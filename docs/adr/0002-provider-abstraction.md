# ADR-0002 — Provider abstraction layer

**Status:** Accepted · 2026-09-19

## Context
The whole business model is "free stack to demo, premium when a client pays." That only works if we can
swap STT/LLM/TTS/embeddings **without code changes**, per tenant, and add vendors easily.

## Decision
Define narrow **Protocol interfaces** per capability in `ofd.providers.base` (STT, LLM, TTS, Embeddings)
with **normalized result types**. A **registry** picks the implementation from `settings.<KIND>_PROVIDER`.
Services/agent depend only on interfaces.

## Why
- Free ↔ premium is an env change (`LLM_PROVIDER=groq` → `anthropic`).
- Per-tenant privacy upgrades (self-hosted for sensitive clients).
- New vendors = implement interface + register + contract test.

## Consequences
- Slight upfront cost writing adapters + normalized types.
- Must maintain a **shared contract test** every provider of a kind must pass.

## Alternatives considered
- Call vendor SDKs directly — fastest to write, but kills the swappability that is our core advantage.
- Use only LiveKit plugins — good for the agent, but we also need providers in API/RAG (embeddings,
  batch STT), so we keep our own thin layer and wrap plugins where useful.
