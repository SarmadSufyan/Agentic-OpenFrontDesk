# 10 — Eval / Simulation Harness

**The differentiator.** You can't ship phone AI you can't test. This harness lets us change prompts and
models with confidence and is the headline "production-grade" story. Lives in `eval/`.

## 1. What it does
Drives the real agent with a **synthetic caller** (an LLM playing a customer) over real audio, runs a
**scenario suite**, and **scores** the outcomes — locally and in CI.

```
scenario (goal + persona + script hints)
  → synthetic caller (LLM) ⇄ OpenFrontDesk agent   (full STT→LLM→TTS→STT loop, or text fast-path)
  → transcript + tool trace + latency
  → scorers → pass/fail + scores
  → report (JSON + human summary); CI gate
```

## 2. Scenarios (`eval/scenarios/`)
Each scenario = YAML/JSON: `id`, `vertical`, caller `goal`, `persona`, optional `script_hints`,
`expected` outcome + assertions. Examples:
- "Book a cleaning for next Tuesday afternoon" → expect `booked`, correct service/date read-back.
- "Do you take walk-ins?" → expect grounded answer from knowledge, no hallucination.
- "Reschedule my Friday appointment" → expect `rescheduled`.
- Angry caller / off-topic / silence / heavy accent / background noise (audio fuzzing).
- "What's the price of X?" where X isn't in the docs → expect refusal + take message.

## 3. Scorers (`eval/scorers/`)
| Scorer | Measures |
|---|---|
| `task_success` | Did it achieve the caller's goal? (deterministic checks on DB state) |
| `grounding` | Were claims supported by retrieved sources? (LLM-judge + source check) |
| `hallucination` | Any unsupported price/hours/policy claim? |
| `booking_correctness` | Right service/time; no double-book; read-back present |
| `interruption` | Did barge-in stop TTS promptly? |
| `latency` | p50/p95 per-turn under budget |
| `safety` | Proper escalation/fallback on failure paths |

## 4. Two speeds
- **Fast (text) mode:** bypass audio; test LLM+tools+RAG logic quickly (runs on every commit).
- **Full (audio) mode:** real STT/TTS loop; measures latency + interruption (runs nightly / pre-release).

## 5. CI gate
- On PRs touching prompts/models/RAG/tools → run fast suite; block merge if pass-rate or grounding drops
  below threshold. Full suite on a schedule. Results tracked over time.

## 6. Why it matters (portfolio + product)
- Turns "it worked when I tried it" into **measured reliability**.
- Directly answers the market's #1 complaint (PoC→production for voice/RAG).
- Reused in the dashboard "Run test scenarios" button for operators. [01](01-product-ux.md).

> Built in Phase 4, but scenarios are collected from Phase 1 onward so we accumulate a real suite.
