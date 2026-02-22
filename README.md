# BazaarYar
An AI-powered marketing assistant that helps businesses manage and optimize their digital marketing efforts.

## Run In Production (Docker Compose)

### 1. Prerequisites
- Docker Engine + Docker Compose plugin installed.
- You can run Docker commands on your host.

### 2. Create the production env file
```bash
cp .env.prod.sample .env.prod
```

### 3. Fill required values in `.env.prod`
- Database:
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Model/provider:
  - `OPENAILIKE_API_KEY`
  - `OPENAILIKE_BASE_URL`
- Frontend/public:
  - `FRONTEND_ORIGINS`
  - `NEXT_PUBLIC_API_BASE_URL` (leave empty for same-origin via Nginx)
  - `NEXT_PUBLIC_PHOENIX_URL` (optional)
- Sandbox:
  - `SANDBOX_DOCKER_IMAGE`
  - `SANDBOX_DOCKER_BIN=docker`
  - `SANDBOX_WORKSPACE_ROOT` (must be an absolute host path)
- App serving port:
  - `APP_PORT` (host port for Nginx, defaults to `80`)

### 4. Build production images
```bash
make prod-build
```

### 5. Start core services
```bash
make prod-up-core
```

This starts:
- `db` (Postgres)
- `phoenix`
- `server` (FastAPI)

### 6. Run database migrations (inside existing `server` container)
```bash
make prod-migrate
```

### 7. Start public-facing services
```bash
make prod-up-edge
```

This starts:
- `web` (Next.js)
- `nginx` (public reverse proxy)

### 8. One-command alternative
```bash
make prod
```

`make prod` runs the same sequence as steps 4-7.

### 9. Access the app
- App: `http://localhost:<APP_PORT>`
- API docs: `http://localhost:<APP_PORT>/api/docs`
- Health: `http://localhost:<APP_PORT>/health`
- Example (default): `http://localhost:80`

### 10. Useful operations
- Stop prod stack:
```bash
make prod-down
```
- Tail prod logs:
```bash
make prod-logs
```

### Sandbox Workspace Troubleshooting
- If you run both prod and dev on the same host, `SANDBOX_WORKSPACE_ROOT` can become root-owned (for example `/tmp/bazaaryar-sandbox`), which can break local dev sandbox writes.
- In non-production environments, the server now falls back to `/tmp/bazaaryar-sandbox-<uid>` when the configured root is not writable.
- In production, the server fails fast. Set `SANDBOX_WORKSPACE_ROOT` to a writable absolute host path and ensure ownership/permissions are correct.
