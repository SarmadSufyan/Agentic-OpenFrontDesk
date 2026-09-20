# 01 — Product & UX

Frontend is intentionally **simple and professional** for v1 (function over form); it will be
redesigned once the system works end-to-end. This doc defines *behavior and flows*, not visual design.

## Personas
- **Owner/Operator** (business owner or their agency): sets up the agent, uploads knowledge, reviews calls.
- **Caller** (the business's customer): phones in, expects fast, correct, human-ish help.
- **Staff** (optional): receives transfers, callbacks, hot-lead alerts.

## The core reframe: "training" = knowledge ingestion
The UI says *"Teach your agent"* with a progress bar. Under the hood there is **no model training** —
we chunk documents, embed them, and index into pgvector for retrieval at call time
(see [05-rag](05-rag.md)). Benefits: instant updates, no GPU, grounded/cited answers, near-zero cost.

## End-to-end flow

```
① Sign up ─► ② Onboarding wizard ─► ③ Test in browser (FREE) ─► ④ Go live (attach phone) ─► ⑤ Operate
```

### ① Sign up → workspace (tenant)
- Email/password (JWT). One user → one or more **workspaces** (tenants). All data scoped by `tenant_id`.

### ② Onboarding wizard (~5 min)
1. **Business profile** — name, type/vertical, hours, address, services, pricing.
2. **Teach the agent (knowledge)** — upload PDF/DOCX, paste text, or paste a **website URL to crawl**.
   → ingestion job → progress → "Knowledge base ready ✅".
3. **Configure the agent** — name, voice, greeting (auto-drafted, editable), tone, **escalation rules**
   (when to transfer / take a message), **booking rules** (durations, buffers, which services).
4. **(Optional) Connect calendar** — Cal.com or Google. Can defer to go-live.

### ③ Test in the dashboard — FREE, browser mic
- **"📞 Talk to your agent"** → speak via mic (WebRTC to LiveKit free tier, no phone number).
- Live side panel: transcript, **retrieved knowledge snippets**, **tool calls** (booked / message / transfer).
- Edit knowledge/greeting → re-test instantly.
- **"Run test scenarios"** → the eval harness plays canned tricky calls → pass/fail report
  (see [10-eval-harness](10-eval-harness.md)).

### ④ Go live (proper setup for their brand)
- Attach a phone number: **buy** a new one or **forward** their existing business line to the agent number.
- Choose provider tier (free self-hosted vs premium cloud) — see [12-costing](12-costing.md).
- **Publish** → real calls handled 24/7.

### ⑤ Operate (daily)
- Calls list → detail (recording, transcript, outcome, cost).
- Bookings & Leads (export / push to CRM).
- Analytics (calls, bookings, deflection %, missed-call recovery, minutes, latency).
- Alerts (Slack/email/SMS) for transfers and hot leads.
- Edit knowledge anytime → re-index → live immediately.

## Screen map (v1)
| Screen | Purpose |
|---|---|
| Public landing | Pitch + live demo number + sign-up |
| Auth | Sign up / log in |
| Onboarding wizard | Profile → Teach → Configure → Calendar |
| Home / Overview | KPI tiles + recent calls |
| Knowledge base | Docs list, add/crawl, re-index, preview chunks |
| Agent config | Voice, greeting, persona, escalation & booking rules |
| 🧪 Test console | Browser call + live transcript + retrieval/tool trace + scenario runner |
| Calls | List → detail (recording, transcript, outcome, cost) |
| Bookings & Leads | Appointments + captured messages, export/CRM |
| Integrations | Calendar, SMS, CRM/webhooks, Slack |
| Analytics | Trends, deflection, latency, usage |
| Settings / Numbers / Billing | Numbers, plan, provider tier, team |

## Key UX principles
- **Never lose a caller.** Any failure path → voicemail/human/callback, never a dead end.
- **Always confirm bookings** by reading them back before writing.
- **Show the work** in the test console (retrieval + tools) so operators trust it.
- **Fast.** Perceived latency is the product; stream everything (see [04-voice-pipeline](04-voice-pipeline.md)).
