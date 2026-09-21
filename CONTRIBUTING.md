# Contributing to OpenFrontDesk

Thanks for your interest! This project aims to be the production-grade, self-hostable open-source AI
voice receptionist. Contributions of all sizes are welcome.

## Dev setup

```bash
cp .env.example .env
docker compose up -d db redis            # Postgres (pgvector) + Redis
pip install -e ".[providers,rag,dev]"    # Python 3.11 or 3.12 recommended
python scripts/init_db.py
python scripts/seed_demo.py              # demo tenant + login + sample data
ofd-api                                  # http://localhost:8000/docs
```

Or just `make demo` (Docker-only, no local Python needed).

## Before you open a PR

```bash
ruff check src tests eval        # lint
ruff format src tests eval       # format
pytest -q                        # unit tests
python -m eval --validate        # scenarios still load
```
CI runs the same checks (`.github/workflows/ci.yml`); please keep it green.

## Conventions

- **Layering:** routers stay thin → call `services/` → which use `models/`, `providers/`, `rag/`.
  Business logic lives in `services/`, never in routers.
- **Providers are edges.** Add an STT/LLM/TTS/embeddings provider by implementing the interface in
  `src/ofd/providers/` and registering it — see [`docs/07-providers.md`](docs/07-providers.md).
- **Tenant scoping:** every tenant-owned query filters by `tenant_id`. Never cross tenants.
- Types everywhere; keep `mypy`/`ruff` clean. UUID PKs, UTC timestamps, money in integer cents.

## Adding an eval scenario

Drop a YAML file in `eval/scenarios/` (see the format in [`eval/README.md`](eval/README.md)) and run
`python -m eval --validate`. Scenarios are how we prove the agent stays accurate.

## Commit / PR style

- Small, focused PRs with a clear description of the change and how you verified it.
- Reference any related issue. Update `docs/` and `progress.md` when behavior changes.

## Reporting bugs / ideas

Open an issue with steps to reproduce (and logs/`/metrics` output where relevant). For security issues,
see [SECURITY.md](SECURITY.md) — please don't file public issues for vulnerabilities.
