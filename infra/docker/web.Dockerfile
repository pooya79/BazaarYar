ARG NODE_IMAGE=node:22-alpine
FROM ${NODE_IMAGE} AS builder

WORKDIR /app/web

RUN corepack enable && corepack prepare pnpm@10.28.2 --activate

COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY web ./

ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_PHOENIX_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_PHOENIX_URL=${NEXT_PUBLIC_PHOENIX_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build \
    && pnpm prune --prod

ARG NODE_IMAGE=node:22-alpine
FROM ${NODE_IMAGE} AS runtime

WORKDIR /app/web

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

RUN corepack enable && corepack prepare pnpm@10.28.2 --activate

COPY --from=builder /app/web/.next ./.next
COPY --from=builder /app/web/public ./public
COPY --from=builder /app/web/node_modules ./node_modules
COPY --from=builder /app/web/package.json ./package.json
COPY --from=builder /app/web/next.config.ts ./next.config.ts

EXPOSE 3000

CMD ["pnpm", "start", "-p", "3000"]
