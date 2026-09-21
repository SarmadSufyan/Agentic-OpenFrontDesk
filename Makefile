.PHONY: help demo install infra-up infra-down initdb seed migrate makemigration dev test lint fmt typecheck up down

help:
	@echo "OpenFrontDesk make targets:"
	@echo "  demo          One command: bring up DB+Redis+API, create tables, seed the demo clinic"
	@echo "  install       Install the package with all extras (dev)"
	@echo "  infra-up      Start Postgres + Redis (docker)"
	@echo "  initdb        Dev bootstrap: pgvector + create tables"
	@echo "  seed          Seed the demo dental clinic + demo login"
	@echo "  migrate       Apply Alembic migrations (alembic upgrade head)"
	@echo "  makemigration Autogenerate a migration:  make makemigration m='msg'"
	@echo "  dev           Run the API locally (ofd-api)"
	@echo "  test          Run pytest"
	@echo "  lint / fmt    Ruff check / format"
	@echo "  typecheck     mypy src"
	@echo "  up / down     docker compose up --build / down"

demo:
	docker compose up -d db redis
	docker compose up -d --build api
	docker compose exec -T api python scripts/init_db.py
	docker compose exec -T api python scripts/seed_demo.py
	@echo ""
	@echo "  ✅ Demo ready -> http://localhost:$${API_HOST_PORT:-8000}/app"
	@echo "     login: demo@openfrontdesk.local / demodemo12"

install:
	pip install -e ".[providers,rag,dev]"

infra-up:
	docker compose up -d db redis

infra-down:
	docker compose down

initdb:
	python scripts/init_db.py

seed:
	python scripts/seed_demo.py

migrate:
	alembic upgrade head

makemigration:
	alembic revision --autogenerate -m "$(m)"

dev:
	ofd-api

test:
	pytest -q

lint:
	ruff check src tests eval

fmt:
	ruff format src tests eval

typecheck:
	mypy src

up:
	docker compose up -d --build db redis api

down:
	docker compose down
