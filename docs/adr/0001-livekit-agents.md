# ADR-0001 — Use LiveKit Agents for voice orchestration

**Status:** Accepted · 2026-09-19

## Context
We need real-time, low-latency audio transport for both **phone (PSTN/SIP)** and **browser (WebRTC)**,
plus an agent runtime that ties STT/LLM/TTS together with interruption handling.

## Decision
Use **LiveKit** (open-source WebRTC media server) + **LiveKit Agents** (Python) as the orchestration layer.

## Why
- One stack for **browser test calls (free)** and **phone calls (SIP)** — critical to the $0-demo model.
- Native **SIP** (no separate Twilio media bridge), **semantic turn detection**, telephony noise
  cancellation, and a **plugin system** for swappable STT/LLM/TTS.
- **Free "Build" tier** (1,000 agent-min/mo) and a **self-hostable** server (Apache-2.0) — same code,
  switch by env. No lock-in.

## Consequences
- Agent runs as its own process/worker pool; one job ≈ one call → scale by replicas.
- We depend on LiveKit's room/worker model; mitigated by it being open-source and self-hostable.

## Alternatives considered
- **Pipecat** — excellent, but LiveKit's native SIP + free tier + browser parity fit our demo model better.
- **Vocode** — smaller ecosystem. **Roll-our-own WebRTC** — too much undifferentiated infra.
