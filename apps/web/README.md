# OpenFrontDesk web app

The product frontend: marketing site, sign-up and onboarding, the dashboard, and the test console.
Next.js 16 (App Router), React 19, Tailwind CSS 4, shadcn/ui (Base UI), SWR, and `livekit-client`
for browser voice calls.

It is a client-rendered app on top of the OpenFrontDesk API: every page is prerendered as static HTML
and talks to the API with a bearer token, so it can be hosted on any static-capable platform.

## Run it

```bash
cp .env.example .env.local      # set NEXT_PUBLIC_API_URL to your API, e.g. http://localhost:8000
npm install
npm run dev                     # http://localhost:3000
```

The API must be running (see the repository README). Sign up at `/signup`, or use the demo account
seeded by `scripts/seed_demo.py`.

```bash
npm run lint     # ESLint, including the React Compiler rules
npm run build    # type-check and production build
```

## Layout

```
src/app/               routes: /, /login, /signup, /onboarding, /contact, /dashboard/*
src/components/        brand, kit (shared primitives), marketing, knowledge, test (chat + voice), settings
src/components/ui/     shadcn/ui components (generated; edit with care)
src/lib/               api client, auth, SWR hooks, types, constants, formatting
```

Design notes, data flow and the full route map are in
[docs/19-frontend.md](../../docs/19-frontend.md).
