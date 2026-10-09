# syntax=docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89
# Shimpz storefront — multi-stage: node prerenders the SvelteKit app (static HTML, best SEO), python
# serves the build, the public catalog, and the OAuth broker (frontend/ + backend/).

# ── stage 1: obtain the exact uv binary without retaining an installer toolchain ─────────────────
FROM ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded AS uv
ARG SOURCE_DATE_EPOCH=0

# ── stage 2: build the prerendered frontend ─────────────────────────────────────────────────────
FROM node:24-slim@sha256:235600a8101ab264e117b1768e925532262668dc9b581ef1dd7d96ced463b8e7 AS web
ARG SOURCE_DATE_EPOCH=0
WORKDIR /w
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN corepack enable \
 && corepack prepare pnpm@11.9.0 --activate \
 && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm test \
 && pnpm run build \
 && find /w/build -depth -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + \
 && rm -rf /root/.cache/node /root/.local/share/pnpm /root/.npm
# adapter-static writes the prerendered site to /w/build

# ── stage 3: resolve target-platform Python dependencies ─────────────────────────────────────────
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS dependencies
ARG SOURCE_DATE_EPOCH=0
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project --no-dev --python 3.14 \
 && rm -rf /root/.cache/uv

# ── stage 4: minimal runtime ─────────────────────────────────────────────────────────────────────
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS serve
ARG SOURCE_DATE_EPOCH=0
RUN groupadd --gid 10008 shimpz-store \
 && useradd --uid 10008 --gid 10008 --no-create-home --shell /usr/sbin/nologin shimpz-store
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/app/__init__.py backend/app/catalog.py backend/app/concurrency.py backend/app/config.py \
     backend/app/control.py backend/app/logconf.py backend/app/main.py backend/app/middleware.py \
     backend/app/oauth_broker.py backend/app/payloads.py backend/app/upstream.py ./app/
COPY backend/app/protocol/http/v1/identifiers.py backend/app/protocol/http/v1/payload.py \
    backend/app/protocol/http/v1/purpose.py backend/app/protocol/http/v1/strict_json.py \
    backend/app/protocol/http/v1/turn.py ./app/protocol/http/v1/
COPY backend/app/routers/__init__.py backend/app/routers/oauth.py backend/app/routers/public.py \
     backend/app/routers/static.py ./app/routers/
COPY --from=web /w/build ./build
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHIMPZ_STORE_BUILD=/app/build
USER 10008:10008
EXPOSE 3200
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=20 \
  CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 3200), 2).close()"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3200"]
