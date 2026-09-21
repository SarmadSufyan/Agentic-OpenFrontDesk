#!/usr/bin/env bash
# One-command demo bring-up.  Usage: bash scripts/demo.sh
set -euo pipefail
docker compose up -d db redis
docker compose up -d --build api
docker compose exec -T api python scripts/init_db.py
docker compose exec -T api python scripts/seed_demo.py
echo ""
echo "  Demo ready -> http://localhost:${API_HOST_PORT:-8000}/app"
echo "  login: demo@openfrontdesk.local / demodemo12"
