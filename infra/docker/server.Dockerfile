FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

COPY server/pyproject.toml server/uv.lock ./server/
RUN uv sync --project server --frozen --no-dev --no-install-project

COPY server ./server

FROM docker:28-cli AS docker_cli

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/server/.venv /app/server/.venv
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
COPY server ./server

ENV PATH="/app/server/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
