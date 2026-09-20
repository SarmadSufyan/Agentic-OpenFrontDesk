# 07 — Providers & Integrations

The heart of "provider-agnostic." Every external AI capability is an interface in `ofd.providers`;
a registry picks the implementation from config. Swapping free ↔ premium is an env change.
See [ADR-0002](adr/0002-provider-abstraction.md).

## 1. Interfaces (`ofd.providers.base`)
```python
class STTProvider(Protocol):
    async def transcribe_stream(self, audio) -> AsyncIterator[STTResult]: ...
    async def transcribe(self, audio: bytes, *, language: str | None = None) -> STTResult: ...

class LLMProvider(Protocol):
    async def complete(self, messages, *, tools=None, stream=True) -> AsyncIterator[LLMDelta]: ...

class TTSProvider(Protocol):
    async def synthesize_stream(self, text: str, *, voice: str) -> AsyncIterator[bytes]: ...

class EmbeddingsProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dim(self) -> int: ...
```
Results/deltas are normalized dataclasses so callers never see vendor shapes.

## 2. Registry
`ofd.providers.registry` maps `settings.<KIND>_PROVIDER` → a factory. `get_stt() / get_llm() /
get_tts() / get_embeddings()` return a configured singleton. Adding a provider = implement the
interface + register it. Unknown value → clear startup error.

## 3. Provider matrix

| Kind | FREE (default) | PREMIUM | Notes |
|---|---|---|---|
| **STT** | Groq Whisper (`whisper-large-v3-turbo`) | Deepgram Nova-3 | Groq free: ~8 hrs audio/day; Deepgram ~150ms streaming |
| **LLM** | Groq Llama-3.1-8B / Gemini 2.5 Flash | Claude Haiku / Gemini paid / GPT | Free tiers ~10–30 RPM (fine for 1 call at a time) |
| **TTS** | Kokoro-82M (self-host, OpenAI-compatible) | Cartesia Sonic-3 | Kokoro = free, CPU, slight latency; Cartesia ~40–60ms |
| **Embeddings** | fastembed (bge-small, CPU) | Gemini `text-embedding-004` | dim fixed per deployment |
| **LLM (dev/offline)** | Ollama (self-host) | — | too slow on CPU for live calls; dev/batch only |

## 4. Telephony & transport
- **Transport:** LiveKit (WebRTC + SIP). Free "Build" tier for browser testing; self-host or paid for scale.
- **Numbers/SIP (go-live):** Telnyx (cheapest inbound ≈ $0.002/min) or Twilio. Behind `ofd.telephony`.
- **Testing needs no telephony** — browser mic over LiveKit = $0. See [08](08-telephony.md).

## 5. Integrations
| Integration | Use | Interface |
|---|---|---|
| Cal.com | Scheduling (open-source) | `ofd.services.booking` |
| Google Calendar | Scheduling (OAuth) | `ofd.services.booking` |
| Twilio / Telnyx SMS | Confirmations/follow-ups | `ofd.telephony.sms` |
| CRM webhook | Push leads/bookings | `ofd.services.jobs` |
| Slack / email | Alerts | `ofd.services.jobs` |

## 6. Cost & privacy notes (per client)
- Free provider tiers may use data to improve their products → OK for demos/non-sensitive; move paying
  or sensitive clients to **paid tiers (no training) or self-hosted**. Toggle per tenant. [13](13-security-compliance.md).
- Per-minute economics and the free→premium upgrade path: [12-costing](12-costing.md).

## 7. Adding a provider (checklist)
1. Implement the interface in `ofd/providers/<kind>/<name>.py`.
2. Register in `registry.py` under its config value.
3. Add env keys to `.env.example` + `ofd.core.config`.
4. Add a contract test (same suite all providers of that kind must pass).
5. Note it in this matrix.
