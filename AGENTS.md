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
- Backend API: FastAPI app in `server/`, served via Uvicorn, with route composition in `server/api/router.py`.
- Services: PostgreSQL (and pgAdmin) via Docker Compose in `infra/`.

### Key Directories
- `infra/`: Local infrastructure setup (Docker Compose, database services, pgAdmin).
- `infra/pgadmin/`: pgAdmin bootstrap files (saved servers and connection auth data).
- `scripts/`: Project utility scripts for local automation and developer workflows.
- `server/`: FastAPI backend application source and Python project config.
- `server/api/`: Backend API routers organized by resource and combined in a main API router.
- `server/api/agents/`: Agent endpoints (`/api/agent`) and resource-specific request/response models.
- `server/api/conversations/`: Conversation endpoints (`/api/conversations`) and related response shaping.
- `server/agents/`: Agent runtime, streaming schema, attachments handling, and model integrations.
- `server/core/`: Core backend settings and environment-driven configuration.
- `server/db/`: SQLAlchemy models, DB session utilities, and Alembic integration.
- `server/db/alembic/`: Migration environment and migration version files.
- `server/domain/`: Domain layer modules for business-centric structures.
- `server/domain/tables/`: Domain table definitions and related persistence mappings.
- `server/tests/`: Backend test suite (API and service-level behavior checks).
- `web/`: Next.js frontend workspace, build/tooling config, and client app source.
- `web/public/`: Static assets served directly by the frontend app.
- `web/src/`: Frontend source code root (routes, views, components, shared libraries).
- `web/src/app/`: Next.js App Router entrypoints, layouts, and route-level UI.
- `web/src/components/`: Reusable UI components and feature-specific component groups.
- `web/src/components/chat-interface/`: Chat experience components (header, input, messages, types/constants).
- `web/src/components/sidebar/`: Sidebar/navigation components for the chat workspace.
- `web/src/components/ui/`: Shared design-system primitives built on Radix + Tailwind.
- `web/src/lib/`: Frontend utilities and shared non-visual logic.
- `web/src/lib/api/`: API client layer (HTTP helpers, typed schemas, and client wrappers).
- `web/src/view/`: Page-level composed views built from components and data hooks.

### Core Frameworks/Libraries
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, lucide-react, class-variance-authority, clsx, tailwind-merge.
- Tooling (frontend): Biome (lint/format), pnpm.
- Backend: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, psycopg, LangChain.
- Tooling (backend): uv (dependency sync), Python >= 3.13.

### Common Commands (Dev/Quality)
- Install deps: `make install` (runs `uv sync` + `pnpm install`).
- Run dev stack: `make dev` (starts DB + backend + frontend).
- Run backend only: `make server`.
- Run backend tests: `make test-server`
- Run frontend only: `make web`.
- Start/stop DB: `make db` / `make db-down`.
- Frontend lint/format: `cd web && pnpm lint` / `pnpm format`.

### Conventions & Constraints
- Use Tailwind theme tokens for styling (avoid literal colors/CSS vars).
- Keep any single file under 700 LOC; split large work into modules.
- Use theme variables when styling pages and components (prefer Tailwind theme tokens over raw CSS variables or literal colors).
- Add code comments on tricky parts
- To load env variables in server you should define them in `server/core/config.py`.
- Use async routes for server
