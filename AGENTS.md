# AGENTS

- Use theme variables when styling pages and components (prefer Tailwind theme tokens over raw CSS variables or literal colors).
- Add code comments on tricky parts
- To load env variables in server you should define them in `server/core/config.py`.
- Use async routes for server

## Project Overview

### High-Level Architecture
- Frontend: Next.js app in `web/` (React + Tailwind CSS + Radix UI).
- Backend API: FastAPI app in `server/`, served via Uvicorn.
- Services: PostgreSQL (and pgAdmin) via Docker Compose in `infra/`.

### Key Directories
- `web/`: Frontend app.
- `web/src/app/`: Next.js App Router routes/layout.
- `web/src/components/`: UI primitives (`ui/`) and marketing UI (`marketing/`).
- `web/src/view/`: Page-level view components.
- `web/src/lib/`: Shared helpers/utilities.
- `server/`: Python backend.
- `server/main.py`: FastAPI entrypoint.
- `server/core/`: Config and environment settings.
- `server/domain/`: Domain models/tables (currently empty scaffolding).
- `server/tests/`: Backend tests (currently empty).
- `infra/`: Docker Compose + pgAdmin config.

### Core Frameworks/Libraries
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, lucide-react, class-variance-authority, clsx, tailwind-merge.
- Tooling (frontend): Biome (lint/format), pnpm.
- Backend: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, psycopg, LangChain.
- Tooling (backend): uv (dependency sync), Python >= 3.13.

### How Agents Should Navigate the Codebase
- Start UI work in `web/src/app/page.tsx` and `web/src/view/`.
- Reuse or extend primitives in `web/src/components/ui/` and feature UI in `web/src/components/marketing/`.
- Check shared helpers in `web/src/lib/utils.ts`.
- Backend routes live in `server/main.py`; settings and DB config in `server/core/config.py`.
- Infra and local services are defined in `infra/docker-compose.yml`.

### Common Commands (Dev/Quality)
- Install deps: `make install` (runs `uv sync` + `pnpm install`).
- Run dev stack: `make dev` (starts DB + backend + frontend).
- Run backend only: `make server`.
- Run frontend only: `make web`.
- Start/stop DB: `make db` / `make db-down`.
- Frontend lint/format: `cd web && pnpm lint` / `pnpm format`.

### Conventions & Constraints
- Use Tailwind theme tokens for styling (avoid literal colors/CSS vars).
- Keep any single file under 700 LOC; split large work into modules.