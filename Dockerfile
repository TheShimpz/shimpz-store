# syntax=docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89
# Shimpz storefront — multi-stage: node prerenders the SvelteKit app (static HTML, best SEO), python
# serves the build, the public catalog, and the OAuth broker (frontend/ + backend/).

# ── stage 1: obtain the exact uv binary without retaining an installer toolchain ─────────────────
FROM ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded AS uv

# ── stage 2: build the prerendered frontend ─────────────────────────────────────────────────────
# The static site is platform-independent, so it is built once on the build platform. The package install precedes
# every commit-bound input, so an unchanged lock reuses it at every commit. The frontend tests run in the gate's
# store-unit lane, not here. No dependency install script runs: the build needs none. adapter-static writes the
# prerendered site to /w/build.
FROM --platform=$BUILDPLATFORM node:24-slim@sha256:235600a8101ab264e117b1768e925532262668dc9b581ef1dd7d96ced463b8e7 AS web
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc /w/
RUN cd /w \
 && corepack enable \
 && corepack prepare pnpm@11.9.0 --activate \
 && pnpm install --frozen-lockfile --ignore-scripts \
 && rm -rf /root/.cache/node /root/.local/share/pnpm /root/.npm
WORKDIR /w
COPY frontend/ ./
ARG SOURCE_DATE_EPOCH=0
RUN pnpm run build \
 && find /w/build -depth -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + \
 && rm -rf /root/.cache/node /root/.local/share/pnpm /root/.npm

# ── stage 3: resolve target-platform Python dependencies ─────────────────────────────────────────
# This layer is the runtime's base and a pure function of the pinned base, uv, and the lock (Shimpz ADR-0098): no ARG
# SOURCE_DATE_EPOCH, WORKDIR, COPY, or ADD here, uv and the lock arrive as read-only mounts on a discarded tmpfs, the uv
# cache is removed, and every /opt timestamp is fixed. The base ships no bytecode and the read-only runtime cannot
# write any, so the standard library and the environment are compiled here, hash-checked, with fixed timestamps.
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS dependencies
RUN --mount=type=tmpfs,target=/tmp \
    --mount=type=bind,from=uv,source=/uv,target=/tmp/uv \
    --mount=type=bind,source=backend/pyproject.toml,target=/tmp/project/pyproject.toml \
    --mount=type=bind,source=backend/uv.lock,target=/tmp/project/uv.lock \
    cd /tmp/project && \
    UV_PROJECT_ENVIRONMENT=/opt/venv UV_CACHE_DIR=/opt/uv-cache UV_LINK_MODE=copy \
        /tmp/uv sync --frozen --no-install-project --no-dev --python 3.14 && \
    rm -rf /opt/uv-cache && \
    find /opt/venv -type f -name '*.pyc' -delete && \
    PYTHONDONTWRITEBYTECODE=1 /opt/venv/bin/python -m compileall -q -f --invalidation-mode checked-hash /usr/local/lib/python3.14 /opt/venv && \
    find /usr/local/lib/python3.14 \( -type d -o -name '*.pyc' \) -exec touch -h -d @0 {} + && \
    find /opt -depth -exec touch -h -d @0 {} +

# ── stage 4: minimal runtime ─────────────────────────────────────────────────────────────────────
# The digest-pinned Python base already retains CA roots; build-only uv never enters an image layer.
FROM dependencies AS serve
ARG SOURCE_DATE_EPOCH=0
RUN groupadd --gid 10008 shimpz-store \
 && useradd --uid 10008 --gid 10008 --no-create-home --shell /usr/sbin/nologin shimpz-store
# Every source copy below is a linked layer that no other copy depends on, so changing one file rebuilds only its own
# layer and the final import check.
WORKDIR /app
COPY --link backend/app/__init__.py backend/app/catalog.py backend/app/concurrency.py backend/app/config.py \
     backend/app/control.py backend/app/logconf.py backend/app/main.py backend/app/middleware.py \
     backend/app/oauth_broker.py backend/app/payloads.py backend/app/ratelimit.py backend/app/upstream.py ./app/
COPY --link backend/app/protocol/http/v1/identifiers.py backend/app/protocol/http/v1/payload.py \
    backend/app/protocol/http/v1/purpose.py backend/app/protocol/http/v1/strict_json.py \
    backend/app/protocol/http/v1/turn.py ./app/protocol/http/v1/
COPY --link backend/app/routers/__init__.py backend/app/routers/oauth.py backend/app/routers/public.py \
     backend/app/routers/static.py ./app/routers/
COPY --link --from=web /w/build ./build
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHIMPZ_STORE_BUILD=/app/build
# Fail during the image build if the explicit copy surface omits an imported module, then compile the application like
# its environment. Compose owns the health probe.
RUN python -c "import app.main" && \
    python -m compileall -q -f --invalidation-mode checked-hash /app/app
USER 10008:10008
EXPOSE 3200
# The access log would record the OAuth callback query (`state`, `code`), so it stays off; request outcomes are logged
# by the application without query values. No forwarded header rewrites the socket peer the start limit reads.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3200", "--no-access-log", "--no-server-header", \
     "--no-proxy-headers"]
