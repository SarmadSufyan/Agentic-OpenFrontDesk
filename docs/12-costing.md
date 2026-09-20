# 12 — Costing & Pricing

Design goal: **≈ $0/month** to build, demo, and show people; add paid providers only when a client is
interested (they fund it). All numbers are 2026 ballparks — verify current provider pricing.

## Tier 0 — Free demo / portfolio (what we build first)
| Component | Choice | Cost |
|---|---|---|
| Voice transport | LiveKit Cloud "Build" | $0 — 1,000 agent-min + 5,000 WebRTC-min/mo, no card |
| STT | Groq Whisper | $0 — ~8 hrs audio/day free |
| LLM | Groq Llama-3.1-8B / Gemini 2.5 Flash | $0 |
| TTS | Kokoro-82M self-hosted | $0 (runs on the VPS CPU) |
| Backend + DB + Redis + RAG + TTS | Hostinger VPS (already owned) | ~$9/mo already paid |
| Dashboard hosting | Vercel free | $0 |
| Telephony | none — browser mic testing | $0 |
| **New monthly spend** | | **≈ $0** |

## Tier 1 — First real client on a phone (still tiny)
- Telnyx number ~$1/mo + inbound ~$0.002/min; keep the free AI stack.
- **≈ $1–10/mo + pennies of usage.** Client pays.

## Tier 2 — Premium / scale (client-funded)
| Piece | Upgrade | Rough cost |
|---|---|---|
| STT | Deepgram Nova-3 | ~$0.004/min |
| TTS | Cartesia Sonic-3 | ~$0.02–0.03/min |
| LLM | Claude Haiku / Gemini Flash (paid) | ~$0.005–0.02/min |
| Transport | LiveKit "Ship" ($50) or self-host | $50/mo or $0 |
| Telephony | Telnyx / Twilio | ~$0.002–0.009/min |
| **All-in** | | **~$0.05–0.10/min** |

- 3-minute call ≈ **$0.15–0.30**. A human receptionist is **$15–25/hr** and misses nights/weekends.

## Using your own assets
- **Google One Pro ≠ API access.** Get a **free Gemini API key from Google AI Studio** (separate, free).
- **Ollama on the VPS:** use for dev/offline/embeddings, **not** live calls (CPU too slow for real-time).
- **Free-tier privacy:** Groq/Gemini free tiers may use data to improve products — fine for demos;
  move paying/sensitive clients to paid (no-training) or self-hosted. Per-tenant toggle.

## Upwork / agency pricing (how this earns)
- **Setup/config fee:** $300–1,500 per client (onboarding, knowledge, number, go-live).
- **Monthly retainer:** $99–499 (hosting, maintenance, updates).
- **Usage:** bundled minutes or pass-through. Your cost is pennies/min → high margin.
- **The pitch:** a live number the client can call *right now* — credibility most freelancers can't match.

## Cost controls in the product
- Per-tenant minute/upload/RPM quotas (Redis). Max call duration + turn caps. Usage tracked per call and
  provider in `usage_event` for billing + analytics. See [14](14-observability.md).
