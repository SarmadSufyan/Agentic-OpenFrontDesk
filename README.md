<div align="center">

# 🎙️ OpenFrontDesk

**The open-source AI voice receptionist for small businesses.**
Answers every call 24/7 · books appointments · answers questions from your own docs · captures leads · hands off to a human.

Self-hostable · provider-agnostic · multi-tenant · actually tested.

</div>

---

## Why this exists

Small businesses miss **30–40% of inbound calls** — every missed call is lost revenue. Hiring a
receptionist is expensive and 9–5. Commercial AI phone SaaS (Vapi, Retell, Bland) is closed and
pricey (advertised rates balloon 3–5× on the real invoice; HIPAA tiers run ~$1k/mo). The existing
open-source projects are thin demos: single-tenant, one hard-wired provider, no tests, no dashboard.

**OpenFrontDesk is the missing middle** — a production-grade platform you can run for **≈ $0/month**
on infrastructure you already own, and upgrade to premium providers per-client when it's earning.

## What makes it production-grade (not a demo)

- 🔌 **Provider-agnostic** — swap STT / LLM / TTS between free (Groq, Gemini, Kokoro) and premium
  (Deepgram, Cartesia, Claude) with a config change, no code edits.
- 🧪 **An eval / call-simulation harness** — synthetic callers run scenario suites in CI so prompt
  and model changes can't silently regress. *Almost no open-source voice project has this.*
- 🏢 **Multi-tenant from day one** — many businesses, isolated data, per-tenant knowledge & config.
- 📚 **Grounded RAG** — answers come from the business's own documents, with citations; if it doesn't
  know, it takes a message instead of hallucinating.
- 💸 **Free to demo** — testing happens over the **browser mic** via LiveKit's free tier; a real phone
  number is only attached at go-live (pennies/minute, on Telnyx/Twilio).

## The flow

```
Sign up → Teach the agent (upload docs / paste website) → Test it in the browser (free)
        → Go live (attach a phone number) → Operate (calls, bookings, leads, analytics)
```

## Architecture at a glance

```
Caller (phone / browser mic)
   → LiveKit (WebRTC + SIP, free tier for testing)
   → Agent worker (Python): VAD → turn detection → STT → LLM (+ RAG + tools) → TTS
        tools: search_knowledge · book_appointment · take_message · transfer_to_human · send_sms
   → FastAPI backend  → Postgres + pgvector · Redis · object storage
   → Next.js dashboard (onboarding, test console, call logs, analytics)
```

Full details in [`docs/02-architecture.md`](docs/02-architecture.md).

## Tech stack

| Layer | Choice |
|---|---|
| Voice orchestration | LiveKit Agents (WebRTC + native SIP) |
| STT | Groq Whisper (free) · Deepgram (premium) |
| LLM | Groq Llama / Gemini Flash (free) · Claude (premium) |
| TTS | Kokoro self-hosted (free) · Cartesia (premium) |
| Backend | Python · FastAPI · SQLAlchemy (async) |
| Data | Postgres + pgvector · Redis |
| Scheduling | Cal.com · Google Calendar |
| Dashboard | Next.js · Tailwind · shadcn/ui |
| Deploy | Docker Compose (self-host) / cloud |

## Quickstart (dev)

```bash
cp .env.example .env          # fill in GROQ_API_KEY, LIVEKIT_* (both have free tiers)
docker compose up -d db redis # Postgres+pgvector and Redis
pip install -e ".[providers,rag,dev]"
alembic upgrade head
ofd-api                       # http://localhost:8000/health  ·  /docs
```

## Documentation

The [`docs/`](docs/) folder has one file per aspect/service — start with
[`docs/00-overview.md`](docs/00-overview.md). Build status lives in [`progress.md`](progress.md).

## License

[Apache-2.0](LICENSE).
