# 19 — Web frontend (Next.js)

The product UI lives in [`apps/web`](../apps/web): the marketing site, sign-up and onboarding, the
dashboard, and the test console. It replaces the single-file `/app` dashboard for end users (that page
still ships with the API as a lightweight admin fallback).

## Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | Next.js 16, App Router, React 19 | Static prerendering, file-based routes, first-class Vercel hosting |
| Styling | Tailwind CSS 4, design tokens as CSS variables | One source of truth for light and dark themes |
| Components | shadcn/ui (`base-nova`, built on Base UI) | Accessible primitives we own and can restyle |
| Data | SWR + a small typed `fetch` client | Caching, polling and revalidation without a heavy client |
| Voice | `livekit-client` (loaded on demand) | Same transport as the voice agent |
| Fonts | Instrument Serif, Hanken Grotesk, JetBrains Mono via `next/font` | Self-hosted at build time, no layout shift |

## Design

The concept is "the front desk that never sleeps": warm and editorial rather than the usual SaaS
gradient.

- **Palette.** Warm paper and ink, a deep evergreen primary, and a vermilion "signal" used only for live,
  real-time moments (an active call, a new request). Full light and dark themes, following the system by
  default with a toggle.
- **Type.** Instrument Serif for display headlines, with italic accents; Hanken Grotesk for the
  interface; JetBrains Mono for code, keys and IDs.
- **Signature.** The landing hero plays a live call: the transcript types itself, a waveform reacts to
  whoever is speaking, and tool calls (`check_availability`, `book_appointment`) and the resulting
  webhook appear as chips. It explains the product in one glance and respects `prefers-reduced-motion`
  by showing the whole conversation statically.
- **Surfaces.** A subtle paper grain and dot grid on marketing pages; calm, bordered panels in the app.

## Routes

| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/contact` | Custom-solutions form (M4 API); `?need=whatsapp` preselects a need |
| `/signup`, `/login` | Account creation and sign-in (`?next=` returns to a same-site page) |
| `/onboarding?step=0..4` | Business, receptionist, knowledge, try it, go live. The step is in the URL so a refresh keeps your place |
| `/dashboard` | Overview: setup checklist, KPIs, latest leads, upcoming bookings |
| `/dashboard/knowledge` | Add text, a web page or a file; live indexing status; "check what it would read" retrieval preview |
| `/dashboard/test` | Chat test (the widget's brain) and voice test (queue-aware LiveKit call with live transcript) |
| `/dashboard/deploy` | Widget snippet, brand color, live preview on the page; phone and WhatsApp status |
| `/dashboard/conversations`, `/leads`, `/bookings` | Activity, with call transcripts in a side panel |
| `/dashboard/integrations` | Webhooks (show-once secret, test, delivery log, rotate) and API keys |
| `/dashboard/settings` | Business profile and hours; receptionist voice, tone, greeting, services, appointment length |
| `/dashboard/admin` | Platform admins only: custom-solution inbox and voice access (sessions, queue, allowlist) |

## How it talks to the API

- `NEXT_PUBLIC_API_URL` points at the FastAPI service. The API allows any origin and uses bearer tokens
  (no cookies), so the frontend can be hosted anywhere.
- `src/lib/api.ts` stores the access and refresh tokens in `localStorage`, attaches the bearer token,
  and on a 401 refreshes once (deduplicated across concurrent requests) before signing out. Network
  failures surface as a clear "cannot reach the API" state instead of a silent logout.
- `src/lib/auth.tsx` reads the token with `useSyncExternalStore` (no hydration mismatch) and loads
  `/auth/me` through SWR. Signing out clears the whole SWR cache, so the next account never sees the
  previous one's data.
- The dashboard is client-rendered behind an auth guard; every route is still prerendered as a static
  shell for fast first paint.
- Knowledge polls every two seconds only while a source is indexing. SWR pauses polling in background
  tabs and revalidates on return.
- Workspace milestones used by the setup checklist (`onboarded`, `tested_at`, `widget_copied_at`) and
  the widget color are stored in the workspace `settings`, which the API now merges instead of
  replacing.

## Voice test console

`components/test/use-voice-session.ts` wraps the M1 access engine:

1. `POST /voice/acquire`: either a LiveKit grant, or a queue position. While queued it asks again every
   five seconds and shows "You are number N in line".
2. Connects with `livekit-client` (imported only when a call starts), publishes the microphone, and
   plays the agent's audio.
3. Transcripts are labelled by participant identity (anything from the local participant is the
   caller), which fixes the earlier test page that mislabelled the caller's words as the agent's.
4. Heartbeats every 45 seconds keep the slot; hang-up, leaving the queue, navigating away, or closing
   the tab (`pagehide` with a keepalive request) releases it.

## Quality bar

- ESLint with the React Compiler rules (no impure calls or ref reads during render, no setState in
  effect bodies) and strict TypeScript, both in CI along with a production build.
- Accessible by default: labelled controls, keyboard-reachable menus and dialogs, `aria-live` chat and
  transcripts, native selects on forms, reduced-motion support, and no horizontal scrolling at 390 px.
- User-supplied content is rendered as text by React (no HTML injection paths).

## Backend changes made while building the UI

Building real screens against the API exposed gaps that are now fixed:

- **Per-agent voice.** The voice worker ignored the agent's configured voice and always used
  `KOKORO_VOICE`; it now uses the agent's voice.
- **Settings merge.** `PATCH /tenants/current` replaced the whole `settings` object; it now merges, and
  `settings` is returned.
- **Chat that knows the date.** The website chat had no idea what day it was, the business hours, or the
  receptionist's tone, and could only list the next five openings. It now gets the local date, a
  ready-made calendar for the coming week, hours, services and tone, and can check a specific day.
- **Time zones west of UTC.** A bare date such as "Sunday" was converted from UTC, turning it into
  Saturday for any business west of UTC. A bare date now means that calendar day where the business is.
- **Closed days.** Asking about a closed day returned the next open day's slots; it now returns none.
- **Stuck indexing.** Hugging Face's Xet transfer protocol stalled indefinitely on some networks, leaving
  documents "pending" forever. The embedding model is now baked into the API and agent images (Xet
  disabled for the download), ingestion has a timeout, and documents orphaned by a restart are marked
  failed with an actionable message at startup.
- **Windows time zones.** `tzdata` is now a dependency, so `zoneinfo` works on Windows hosts instead of
  silently falling back to UTC.

## Verification

- Sign-up through the UI, all five onboarding steps against the live API, then the dashboard with the
  setup checklist reflecting server state.
- Knowledge added through the UI indexed and was used by the test chat to answer "Sports massage is $70
  ... We do not offer home visits" with its source cited.
- Deploy: color saved, snippet updated, the real widget injected in that color and fully removed.
- Settings: hours, services and appointment length saved; earlier settings keys preserved.
- Headless Chrome screenshots of every route in light and dark at 1440 px and at 390 px: no page or
  console errors and no horizontal overflow.
- Unit tests for the scheduling fixes (four time zones, closed days) and the chat prompt.
