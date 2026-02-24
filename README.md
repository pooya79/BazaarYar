# BazaarYar

BazaarYar is a marketing agent platform with a ChatGPT-style interface.
It helps teams analyze campaign data, generate strategy ideas, and persist reusable memory through conversation reports and prompt templates.

## What It Does

- Chat-based marketing assistant with streaming responses.
- Attachment upload and analysis (CSV, TSV, TXT, PDF, XLSX, images).
- Conversation persistence with rename/star/delete and pagination.
- Saved conversation reports for long-term memory (`/api/reports`).
- Prompt library with `\prompt-name` insertion in chat (`/api/prompts`).
- Model cards, company profile, and tool toggles in settings (`/api/settings`).
- Optional Python sandbox tool for isolated code execution and artifact generation.
- Optional Phoenix observability integration.

## Architecture

- Frontend: Next.js 16 + React 19 in [`web/`](web)
- Backend: FastAPI + SQLAlchemy in [`server/`](server)
- Database/infra: PostgreSQL + pgAdmin + Phoenix via Docker Compose in [`infra/`](infra)

Key backend API composition happens in [`server/api/router.py`](server/api/router.py), which mounts:

- `/api/agent/*`
- `/api/conversations/*`
- `/api/settings/*`
- `/api/reports/*`
- `/api/prompts/*`

## Tech Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS v4, Radix UI, Zod, Zustand.
- Backend: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, LangChain.
- Tooling: `uv` (Python deps), `pnpm` (web deps), Docker Compose.
- Runtime requirements: Python `>=3.13`, Node `22+`, pnpm `10+`.

## Repository Layout

```text
.
├── infra/                # Docker compose files, nginx, sandbox image, pgAdmin bootstrap
├── scripts/              # Utility scripts for seeding and cleanup
├── server/               # FastAPI app (api, features, db, tests)
│   ├── api/              # API composition
│   ├── core/             # Settings/config
│   ├── db/               # SQLAlchemy models + Alembic
│   ├── features/         # Feature-sliced backend modules
│   └── tests/            # Backend tests
└── web/                  # Next.js app (app routes, features, shared)
```

## Local Development

### 1. Prerequisites

- Python 3.13+
- `uv`
- Node.js 22+
- `pnpm`
- Docker Engine + Docker Compose plugin

### 2. Bootstrap environment

```bash
cp .env.sample .env
```

Important defaults already exist in `.env.sample` for local development.

### 3. Install dependencies

```bash
make install
```

This runs:

- `uv sync --group dev` in `server/`
- `pnpm install` in `web/`

### 4. Start infra + apps

```bash
make dev
```

This starts:

- Infra (`db`, `pgadmin`, `phoenix`) via `infra/docker-compose.yml`
- Backend (`uvicorn server.main:app --reload`)
- Frontend (`pnpm dev`)

### 5. Access local services

- Web app: http://localhost:3000
- Backend API docs: http://localhost:8000/api/docs
- Backend health: http://localhost:8000/health
- Phoenix UI: http://localhost:6006
- pgAdmin: http://localhost:5050

### Useful local commands

```bash
make infra          # start db + pgAdmin + phoenix
make infra-down     # stop infra
make server         # backend only
make web            # frontend only
make db             # start postgres only
make db-down        # stop postgres container
make phoenix        # start phoenix only
make phoenix-down   # stop phoenix container
```

## Environment Configuration

Server settings are defined in [`server/core/config.py`](server/core/config.py). Frontend env validation is in [`web/src/shared/api/schemas/env.ts`](web/src/shared/api/schemas/env.ts).

### Core backend vars

- `ENVIRONMENT`
- `DATABASE_URL` (optional; overrides discrete DB fields)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSL_MODE`
- `FRONTEND_ORIGINS` (comma-separated CORS allowlist)

### Model/provider vars

- `OPENAILIKE_MODEL`
- `OPENAILIKE_API_KEY`
- `OPENAILIKE_BASE_URL`
- `OPENAILIKE_TEMPERATURE`
- `OPENAILIKE_REASONING_EFFORT` (`low|medium|high`)
- `OPENAILIKE_REASONING_ENABLED`

Note: `.env.sample` also contains `OPENAI_*` and `GEMINI_*` placeholders, but current server runtime settings are resolved from `OPENAILIKE_*` and DB model cards.

Model resolution precedence in agent requests:

1. Explicit `model_id` request field (and optionally set active).
2. Active model card in DB.
3. Default model card in DB.
4. Env defaults above.

### Upload/attachment vars

- `UPLOAD_STORAGE_DIR` (default `server/storage/uploads`)
- `UPLOAD_MAX_SIZE_BYTES` (default 15MB)

### Context-window vars

- `CONTEXT_MAX_TOKENS`
- `CONTEXT_TARGET_TOKENS`
- `CONTEXT_KEEP_LAST_TURNS`

### Sandbox vars

- `SANDBOX_TOOL_ENABLED`
- `SANDBOX_DOCKER_IMAGE`
- `SANDBOX_DOCKER_BIN`
- `SANDBOX_WORKSPACE_ROOT` (must be absolute)
- `SANDBOX_MAX_RUNTIME_SECONDS`
- `SANDBOX_MAX_MEMORY_MB`
- `SANDBOX_MAX_CPU`
- `SANDBOX_MAX_ARTIFACTS`
- `SANDBOX_MAX_ARTIFACT_BYTES`
- `SANDBOX_MAX_CODE_CHARS`
- `SANDBOX_PERSIST_SESSIONS`
- `SANDBOX_SESSION_IDLE_TTL_SECONDS`
- `SANDBOX_SESSION_POLL_INTERVAL_MS`
- `SANDBOX_SESSION_QUEUE_WAIT_TIMEOUT_SECONDS`
- `SANDBOX_SESSION_SWEEP_INTERVAL_SECONDS`

Non-production fallback behavior:

- If `SANDBOX_WORKSPACE_ROOT` is unusable, the app falls back to `/tmp/bazaaryar-sandbox-<uid>`.
- In production, unusable workspace root is a hard failure.

### Frontend vars

- `NEXT_PUBLIC_API_BASE_URL` (optional; empty means same-origin requests)
- `NEXT_PUBLIC_PHOENIX_URL` (optional; toggles Phoenix button in UI)

## Database and Migrations

### Run migrations locally

```bash
make db-migrate
```

### Downgrade one migration

```bash
make db-downgrade
```

Alembic config and versions:

- [`server/db/alembic.ini`](server/db/alembic.ini)
- [`server/db/alembic/versions/`](server/db/alembic/versions)

## API Overview

OpenAPI docs: `/api/docs`

### System

- `GET /` (service status payload)
- `GET /health`
- `POST /api/sweep-sandbox` (manual cleanup trigger)

### Agent

- `GET /api/agent/stream/schema`
- `POST /api/agent`
- `POST /api/agent/stream`
- `POST /api/agent/attachments`
- `GET /api/agent/attachments/{attachment_id}/content`
- `POST /api/agent/conversations/{conversation_id}/sandbox/reset`

### Conversations

- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/context-window`
- `PATCH /api/conversations/{conversation_id}/title`
- `PATCH /api/conversations/{conversation_id}/star`
- `DELETE /api/conversations/{conversation_id}`

### Settings

- Models: `/api/settings/models*`
- Tool settings: `/api/settings/tools`
- Company profile: `/api/settings/company`

### Reports and prompts

- Reports CRUD/search: `/api/reports`
- Prompt templates CRUD/search: `/api/prompts`

## Streaming Protocol (`/api/agent/stream`)

Response type: Server-Sent Events (SSE).

Events currently emitted:

- `text_delta`
- `reasoning_delta`
- `tool_call_delta`
- `tool_call`
- `tool_result`
- `sandbox_status`
- `conversation`
- `final`

Schema endpoint:

- `GET /api/agent/stream/schema`

## Sandbox Tool

Build sandbox image:

```bash
make sandbox-image
```

The sandbox runtime executes containers with strict isolation flags:

- `--network none`
- `--read-only`
- `--cap-drop ALL`
- `--security-opt no-new-privileges`
- pid/memory/cpu limits

Generated artifacts are persisted as attachments and returned in streamed tool result payloads.

More details: [`infra/sandbox/README.md`](infra/sandbox/README.md)

## Testing and Quality

Run backend tests:

```bash
make test-server
```

Run frontend lint:

```bash
cd web && pnpm lint
```

Run frontend formatter:

```bash
cd web && pnpm format
```

## Data Utilities

### Seed synthetic conversations

```bash
make seed-conversations "ARGS=--count 200 --yes"
```

Dry run:

```bash
make seed-conversations "ARGS=--count 200 --dry-run"
```

### Clear development conversations and linked files

Dry run:

```bash
make clear-dev-conversations "ARGS=--dry-run"
```

Execute:

```bash
make clear-dev-conversations "ARGS=--yes"
```

## Production Deployment (Docker Compose)

### 1. Prepare env file

```bash
cp .env.prod.sample .env.prod
```

Fill required values in `.env.prod`, especially:

- DB credentials (`DB_*`, `POSTGRES_*`)
- `OPENAILIKE_API_KEY` and `OPENAILIKE_BASE_URL`
- `FRONTEND_ORIGINS`
- `SANDBOX_WORKSPACE_ROOT` (absolute writable host path)
- `APP_PORT`
- Optional image override: `NODE_IMAGE`

### 2. Build images

```bash
make prod-build
```

### 3. Start core services

```bash
make prod-up-core
```

Starts: `db`, `phoenix`, `server`.

### 4. Run migrations

```bash
make prod-migrate
```

### 5. Start edge services

```bash
make prod-up-edge
```

Starts: `web`, `nginx`.

### 6. One-command sequence

```bash
make prod
```

Equivalent to steps 2-5.

### 7. Access production stack

- App: `http://localhost:<APP_PORT>`
- API docs: `http://localhost:<APP_PORT>/api/docs`
- Health: `http://localhost:<APP_PORT>/health`

### 8. Operate stack

```bash
make prod-logs
make prod-down
```

## Notes

- Backend docs are always served from `/api/docs`.
- Prompt library persistence is backend-owned (`/api/prompts`) and used by chat slash insertion.
- API keys are masked in settings read responses (preview only, no full secret echo).

## License

MIT. See [`LICENSE`](LICENSE).
