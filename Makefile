SHELL := /bin/bash

.PHONY: install install-server install-web dev server test-server web db db-down db-migrate db-downgrade

install: install-server install-web

install-server:
	cd server && uv sync

install-web:
	cd web && pnpm install

dev: db
	$(MAKE) -j 2 server web

server:
	source server/.venv/bin/activate && python -m uvicorn server.main:app --reload

test-server:
	source server/.venv/bin/activate && python -m pytest server/tests

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
