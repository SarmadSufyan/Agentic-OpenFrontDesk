# 04 — Voice Agent Pipeline

Runs in `ofd.agent` on a LiveKit worker. One worker job = one live call. Chained pipeline is the
default (control + cost + testability); speech-to-speech is an optional premium mode
([ADR-0004](adr/0004-chained-pipeline.md)).

## 1. Pipeline stages

```
mic/phone audio
  → VAD (Silero)                     # is someone speaking?
  → turn detection                   # has the caller finished their turn?
  → STT (streaming, partials)        # audio → text
  → LLM (system prompt + tools + history)
        ├─ tool calls → ofd.services (knowledge, booking, message, transfer, sms)
        └─ streamed text (sentence by sentence)
  → TTS (stream first sentence ASAP) # text → audio
  → back to caller
```

## 2. Latency (the product)
- Human turn-taking gap ≈ 200ms; conversational threshold ≈ 250–300ms; acceptable phone agent < ~800ms.
- **Techniques:** stream STT partials; start LLM on first stable partial; **start TTS on the first
  sentence** before the LLM finishes; keep prompts tight; cache tenant config.
- **Budget (free stack):** p50 < 700ms, p95 < 1100ms (Kokoro CPU TTS dominates variance).
- **Budget (premium):** p50 ≈ 400ms with Cartesia + Deepgram.
- Latency is logged per turn (STT/LLM/TTS split) and asserted in the eval harness.

## 3. Turn detection & barge-in
- VAD (Silero) for speech presence; semantic/adaptive turn detection to avoid cutting people off mid-sentence.
- **Barge-in:** if the caller speaks while the agent is talking, stop TTS immediately and listen.
- Tunable silence thresholds per tenant (some verticals speak slower).

## 4. Prompt structure
System prompt is assembled per call from tenant config:
- **Identity/persona:** business name, agent name, tone.
- **Capabilities & rules:** hours, services, booking rules, escalation rules.
- **Grounding rule:** answer only from retrieved knowledge; if not found → take a message / transfer;
  never invent prices, availability, or policy.
- **Tools** (function calling): described below.
- **Guardrails:** stay on topic, confirm bookings by read-back, capture caller name+number.

## 5. Tools (function calling → `ofd.agent.tools`, delegating to `ofd.services`)
| Tool | Does | Service |
|---|---|---|
| `search_knowledge(query)` | Retrieve grounded snippets (+source ids) | `rag.retrieve` |
| `check_availability(service, date_range)` | Free slots | `booking` |
| `book_appointment(...)` | Create booking (idempotent) + read-back | `booking` |
| `reschedule` / `cancel` | Modify booking | `booking` |
| `take_message(...)` / `capture_lead(...)` | Persist message/lead | `leads` |
| `transfer_to_human()` / `request_callback()` | Warm transfer / callback | `calls`/`telephony` |
| `send_sms(...)` | Post-call confirmation/follow-up | `telephony` (enqueued) |

Tool calls are logged (name, args, result, latency) → shown in the test console and stored on the call.

## 6. Safety & fallbacks (never lose a caller)
- STT/LLM/TTS error or timeout → apologize + retry once → else offer callback/voicemail/human.
- Unknown/hostile input → de-escalate, offer human.
- Booking write failure → do **not** claim success; take a message + alert staff.
- Max turn count / call duration guard to avoid runaway calls (cost control).

## 7. Recording & consent
- Optional per-tenant recording with a consent line at call start (region-configurable). [13](13-security-compliance.md).
- Recording stored in object storage; URL on the `call` row; transcript always stored.

## 8. Observability per call
- Per-turn timings, tokens, provider costs; full transcript; tool trace; outcome enum
  (`booked`, `message_taken`, `transferred`, `answered`, `abandoned`, `failed`). → [14](14-observability.md).

## 9. Testing the pipeline
- The eval harness ([10](10-eval-harness.md)) drives the agent with a synthetic caller over real audio
  and scores booking success, grounding, interruption handling, and latency — gated in CI.
