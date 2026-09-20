.PHONY: help install infra-up infra-down initdb migrate makemigration dev test lint fmt typecheck up down

help:
	@echo "OpenFrontDesk make targets:"
	@echo "  install       Install the package with all extras (dev)"
	@echo "  infra-up      Start Postgres + Redis (docker)"
	@echo "  initdb        Dev bootstrap: pgvector + create tables"
	@echo "  migrate       Apply Alembic migrations (alembic upgrade head)"
	@echo "  makemigration Autogenerate a migration:  make makemigration m='msg'"
	@echo "  dev           Run the API locally (ofd-api)"
	@echo "  test          Run pytest"
	@echo "  lint / fmt    Ruff check / format"
	@echo "  typecheck     mypy src"
	@echo "  up / down     docker compose up --build / down"

install:
	pip install -e ".[providers,rag,dev]"

infra-up:
	docker compose up -d db redis

infra-down:
	docker compose down

initdb:
	python scripts/init_db.py

migrate:
	alembic upgrade head

makemigration:
	alembic revision --autogenerate -m "$(m)"

dev:
	ofd-api

test:
	pytest -q

lint:
	ruff check src tests

fmt:
	ruff format src tests

typecheck:
	mypy src

up:
	docker compose up -d --build db redis api

down:
	docker compose down
