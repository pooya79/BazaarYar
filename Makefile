SHELL := /bin/bash

.PHONY: install install-server install-web dev server test-server web infra infra-down db db-down phoenix phoenix-down db-migrate db-downgrade sandbox-image clear-dev-conversations seed-conversations

ARGS ?=

install: install-server install-web

install-server:
	cd server && uv sync --group dev

install-web:
	cd web && pnpm install

dev: infra
	$(MAKE) -j 2 server web

server:
	uv run --project server uvicorn server.main:app --reload

test-server:
	PYTHONPATH=. uv run --project server python -m pytest server/tests

web:
	cd web && set -a && . ../.env && set +a && pnpm dev

infra:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

db:
	docker compose -f infra/docker-compose.yml up -d db

db-down:
	docker compose -f infra/docker-compose.yml stop db

phoenix:
	docker compose -f infra/docker-compose.yml up -d phoenix

phoenix-down:
	docker compose -f infra/docker-compose.yml stop phoenix

db-migrate:
	source server/.venv/bin/activate && alembic -c server/db/alembic.ini upgrade head

db-downgrade:
	source server/.venv/bin/activate && alembic -c server/db/alembic.ini downgrade -1

sandbox-image:
	docker build -t bazaaryar-python-sandbox:latest infra/sandbox

clear-dev-conversations:
	# Deletes all conversation/message/attachment DB records and linked files.
	# example: make clear-dev-conversations "ARGS=--dry-run"
	# ARGS:
	# --dry-run: preview counts only (no deletion)
	# --yes: execute deletion
	# --force: allow run outside dev-like DB targets
	PYTHONPATH=. uv run --project server python scripts/clear_dev_conversations.py $(ARGS)

seed-conversations:
	# Seeds synthetic conversations/messages for sidebar pagination/load testing.
	# example: make seed-conversations "ARGS=--count 200 --dry-run"
	# ARGS:
	# --count <int> (required): number of conversations to create
	# --messages-per-conversation <int> (default: 4)
	# --title-prefix <string> (default: "Seed Conversation")
	# --minutes-between-conversations <int> (default: 15)
	# --batch-size <int> (default: 100)
	# --dry-run: preview seeding plan only
	# --yes: execute seeding
	# --force: allow run outside dev-like DB targets
	PYTHONPATH=. uv run --project server python scripts/seed_conversations.py $(ARGS)
