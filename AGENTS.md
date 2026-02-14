# AGENTS

## Project Overview

### Product Vision
This project is building a marketing agent with a ChatGPT-like interface.
Its goal is to help marketing teams turn campaign data into clear insights and actionable next steps.

Users can:
- Upload campaign reports and ask questions about performance.
- Request new campaign ideas and strategy suggestions.
- Create dynamic report tables that agents can query for analytics (aggregations, filtering, and data exploration).

The agent platform is designed to support:
- Memory across conversations.
- Tool calling for structured actions and data workflows.
- Multimedia inputs (for example files and other non-text context sources).

### High-Level Architecture
- Frontend: Next.js app in `web/` (React + Tailwind CSS + Radix UI).
  Frontend is organized as feature-first modules in `web/src/features/*` with shared primitives/services in `web/src/shared/*`.
- Backend API: FastAPI app in `server/`, served via Uvicorn.
  Backend business logic is feature-sliced under `server/features/*`, with API composition in `server/api/router.py` (including `/api/agent/*`, `/api/settings/*`, `/api/tables/*`, and chat/attachment routes).
- Services: PostgreSQL (and pgAdmin) via Docker Compose in `infra/`.

### Key Directories
- `infra/`: Local infrastructure setup (Docker Compose, database services, pgAdmin).
- `infra/pgadmin/`: pgAdmin bootstrap files (saved servers and connection auth data).
- `scripts/`: Project utility scripts for local automation and developer workflows.
- `server/`: FastAPI backend application source and Python project config.
- `server/api/`: Backend API composition root.
- `server/features/`: Canonical backend feature slices (`agent`, `settings`, `attachments`, `chat`, `tables`, `shared`).
- `server/features/agent/`: Agent feature modules (API routing, streaming orchestration, runtime/service adapters, tools, model integration, python sandbox tool).
- `server/features/settings/`: Global app settings feature modules (model settings repo/service/API under `/api/settings`).
- `server/features/attachments/`: Attachment feature modules (storage, metadata, upload/download API).
- `server/features/chat/`: Conversation/chat feature modules (context windowing, persistence orchestration, API).
- `server/features/tables/`: Reference table feature modules (schema/query/import/service/API).
- `server/features/shared/`: Shared backend helpers (for example UUID parsing utilities).
- `server/core/`: Core backend settings and environment-driven configuration.
- `server/db/`: SQLAlchemy models, DB session utilities, and Alembic integration.
- `server/db/models/`: SQLAlchemy model modules split by domain (`agent.py`, `chat.py`, `attachments.py`, `tables.py`) with stable exports in `__init__.py`.
- `server/db/alembic/`: Migration environment and migration version files.
- `server/tests/`: Backend test suite (API and service-level behavior checks).
- `server/tests/architecture/`: Import-boundary guardrail tests for backend layering and coupling constraints.
- `web/`: Next.js frontend workspace, build/tooling config, and client app source.
- `web/public/`: Static assets served directly by the frontend app.
- `web/src/`: Frontend source code root (app routes, features, and shared modules).
- `web/src/app/`: Next.js App Router entrypoints, layouts, and route-level UI.
- `web/src/features/`: Feature modules with local components/hooks/model/utils and feature entrypoints.
- `web/src/features/chat/`: Chat feature implementation (chat page, streaming/session hooks, timeline utilities, model/types).
- `web/src/features/reference-tables/`: Reference tables feature implementation (list/detail pages, query/mutation hooks, utilities).
- `web/src/shared/`: Cross-feature shared modules.
- `web/src/shared/ui/`: Shared design-system primitives built on Radix + Tailwind.
- `web/src/shared/layout/`: App shell and shared workspace layout components.
- `web/src/shared/api/`: API client layer (HTTP helpers, typed schemas, and client wrappers).
- `web/src/shared/lib/`: Generic non-visual utilities.

### Core Frameworks/Libraries
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, lucide-react, class-variance-authority, clsx, tailwind-merge, zustand.
- Tooling (frontend): Biome (lint/format), pnpm.
- Backend: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, psycopg, LangChain.
- Tooling (backend): uv (dependency sync), Python >= 3.13.

### Common Commands (Dev/Quality)
- Install deps: `make install` (runs `uv sync --group dev` + `pnpm install`).
- Run dev stack: `make dev` (starts infra + backend + frontend).
- Run backend only: `make server`.
- Run backend tests: `make test-server`
- Run frontend only: `make web`.
- Start/stop infra services: `make infra` / `make infra-down`.
- Start/stop DB only: `make db` / `make db-down`.
- Start/stop Phoenix only: `make phoenix` / `make phoenix-down`.
- Frontend lint/format: `cd web && pnpm lint` / `pnpm format`.

### Conventions & Constraints
- Use Tailwind theme tokens for styling (avoid literal colors/CSS vars).
- Keep any single file under 700 LOC; split large work into modules.
- Use theme variables when styling pages and components (prefer Tailwind theme tokens over raw CSS variables or literal colors).
- Add code comments on tricky parts
- Keep route files in `web/src/app/*` thin and import feature pages from feature entrypoints (`@/features/chat`, `@/features/reference-tables`).
- Put feature-specific logic under `web/src/features/<feature>/*`; put cross-feature code under `web/src/shared/*`.
- Avoid new imports from compatibility layers (`web/src/components/*`, `web/src/lib/*`) unless maintaining legacy paths.
- Put canonical backend business logic under `server/features/*`; keep `server/api/router.py` composition-only.
- Import backend functionality from canonical modules under `server/features/*` and `server/db/models/*`.
- To load env variables in server you should define them in `server/core/config.py`.
- Use async routes for server
- Agent model settings precedence: use DB global settings from `server/features/settings` when present, otherwise fallback to env defaults from `server/core/config.py`.
- Never commit real API keys to repo files. Settings read APIs should return masked key previews only (no full secret echo).
