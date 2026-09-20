# ADR-0004 — Chained pipeline as default (speech-to-speech optional)

**Status:** Accepted · 2026-09-19

## Context
Two voice architectures: **chained** (STT → LLM → TTS as separate models) vs **speech-to-speech**
(one realtime model, audio in/audio out, e.g. OpenAI Realtime / Gemini Live).

## Decision
Default to the **chained** pipeline. Offer speech-to-speech as an **optional premium mode**.

## Why
- **Swappability & cost:** mix free providers (Groq + Kokoro) → the $0 stack. S2S locks us to one paid vendor.
- **Control & grounding:** we see the text between stages → enforce RAG grounding, run tools reliably,
  redact PII, and **test/score** each stage. Essential for the eval harness and trust story.
- **Testability:** text fast-path in the eval harness needs discrete stages.

## Consequences
- Slightly higher latency than the best S2S; mitigated by streaming each stage and premium TTS.
- More components to orchestrate (handled by LiveKit Agents).

## Alternatives considered
- **S2S by default** — most natural feel, lowest latency, but sacrifices cost control, grounding
  enforcement, and testability. Kept as an upsell for clients who want it and will pay.
