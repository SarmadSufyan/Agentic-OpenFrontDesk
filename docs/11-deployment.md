# 11 — Deployment

Everything runs via Docker Compose. Default target: one Hostinger KVM VPS + Vercel (dashboard) + free
managed tiers (LiveKit, Groq, Gemini). New monthly cost ≈ $0. See [12-costing](12-costing.md).

## 1. Services (`docker-compose.yml`)
| Service | Image / build | Port | Notes |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | 5432 | Postgres + pgvector |
| `redis` | `redis:7-alpine` | 6379 | cache/queue |
| `api` | build `deploy/Dockerfile.api` | 8000 | FastAPI (uvicorn) |
| `agent` | build `deploy/Dockerfile.agent` | — | LiveKit worker (add in Phase 1) |
| `kokoro` | Kokoro-FastAPI image | 8880 | free TTS (OpenAI-compatible) |
| `nginx` | `nginx:alpine` | 80/443 | reverse proxy + TLS (prod) |

Dev shortcut: `docker compose up -d db redis` then run `ofd-api` on the host.

## 2. Local dev
```bash
cp .env.example .env            # set GROQ_API_KEY, LIVEKIT_* (free tiers)
docker compose up -d db redis
pip install -e ".[providers,rag,dev]"
alembic upgrade head
ofd-api                         # http://localhost:8000/health  ·  /docs
```

## 3. VPS (Hostinger) recommended specs
- **KVM 2 (8GB RAM, 2 vCPU, 100GB NVMe)** — comfortable for demo + a few concurrent calls, and to run
  Kokoro (CPU TTS) + Postgres + Redis + API + agent.
- KVM 4 (16GB) if also running Ollama for dev/offline (not for live calls).
- No GPU needed — heavy AI (STT/LLM) uses Groq/Gemini free tiers over the network.

## 4. Production bring-up
```bash
git clone <repo> && cd openfrontdesk
cp .env.example .env            # production secrets; ENV=production, LOG_JSON=true
docker compose --profile prod up -d --build
docker compose exec api alembic upgrade head
# point DNS + nginx TLS (certbot) at the VPS; deploy dashboard to Vercel → API URL
```

## 5. Config profiles
- **Free:** `STT=groq LLM=groq/gemini TTS=kokoro EMBEDDINGS=fastembed TELEPHONY=none` (browser testing).
- **Premium:** switch to `deepgram/cartesia/anthropic`, set `TELEPHONY=telnyx`, add numbers. No code change.

## 6. Data & backups
- Postgres nightly `pg_dump` (Hostinger weekly backups too). Object storage: local dir (free) → S3/MinIO.
- Migrations are forward-only; test on a copy before prod.

## 7. Scaling
- More concurrent calls → more `agent` replicas (1 call ≈ 1 worker job).
- API → multiple replicas behind nginx. Postgres → pooler + read replica later.
- Move off free tiers per busy/paying tenant (per-tenant provider config).

## 8. Health & readiness
- `GET /health` (liveness) and `GET /health?deep=1` (DB + Redis checks) for compose/uptime monitors.
