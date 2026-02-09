SHELL := /bin/bash

.PHONY: install install-server install-web dev server test-server web db db-down db-migrate db-downgrade sandbox-image

install: install-server install-web

install-server:
	cd server && uv sync --group dev

install-web:
	cd web && pnpm install

dev: db
	$(MAKE) -j 2 server web

server:
	uv run --project server uvicorn server.main:app --reload

test-server:
	PYTHONPATH=. uv run --project server python -m pytest server/tests

web:
	cd web && set -a && . ../.env && set +a && pnpm dev

db:
	docker compose -f infra/docker-compose.yml up -d

db-down:
	docker compose -f infra/docker-compose.yml down

db-migrate:
	source server/.venv/bin/activate && alembic -c server/db/alembic.ini upgrade head

db-downgrade:
	source server/.venv/bin/activate && alembic -c server/db/alembic.ini downgrade -1

sandbox-image:
	docker build -t bazaaryar-python-sandbox:latest infra/sandbox
