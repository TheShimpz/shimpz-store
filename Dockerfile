# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
# Shimpz storefront — multi-stage: node prerenders the SvelteKit app (static HTML, best SEO), and one Rust binary
# serves the build, the public catalog, and the OAuth broker (frontend/ + backend/, ADR-0123 R3).

# ── build the prerendered frontend ──────────────────────────────────────────────────────────────
# The static site is platform-independent, so it is built once on the build platform. The package install precedes
# every commit-bound input, so an unchanged lock reuses it at every commit. The frontend tests run in the gate's
# store-unit lane, not here. No dependency install script runs: the build needs none. adapter-static writes the
# prerendered site to /w/build.
FROM --platform=$BUILDPLATFORM node:26.11.1-bookworm-slim@sha256:86f07bc9c5dce4578cf37e5a418b7bfc7f817cda25cde66e2b66e95ed86c4567 AS web
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc \
     frontend/bootstrap-pnpm.sh /w/
# Node.js 26 bundles no Corepack: bootstrap-pnpm.sh installs the exact pnpm the manifest names from its registry
# tarball, verified against the sha256 the script pins.
ENV PATH="/opt/pnpm/bin:$PATH"
RUN cd /w \
 && sh bootstrap-pnpm.sh /tmp/pnpm-cache /opt/pnpm \
 && rm -rf /tmp/pnpm-cache \
 && pnpm install --frozen-lockfile --ignore-scripts \
 && rm -rf /root/.cache/pnpm /root/.local/share/pnpm /root/.npm
WORKDIR /w
COPY frontend/ ./
ARG SOURCE_DATE_EPOCH=0
RUN pnpm run build \
 && find /w/build -depth -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + \
 && rm -rf /root/.cache/pnpm /root/.local/share/pnpm /root/.npm

# ── the Rust Store ──────────────────────────────────────────────────────────────────────────────
# The packages as the dependency build sees them: every manifest and lockfile, and a stub in place of each library and
# binary root, so a source edit leaves the dependency layer unchanged.
FROM docker.io/library/rust:1.99.0-trixie@sha256:6ff07edce8775d0f64be7aba9197229407301bddf2054d62c27b541a6238a181 AS rust-skeleton
WORKDIR /workspace
COPY backend/Cargo.toml backend/Cargo.lock ./backend/
COPY backend/src ./backend/src
COPY vendor/strict-json ./vendor/strict-json
COPY protocol/team/http ./protocol/team/http
RUN find . -type f -regextype posix-extended \
        ! -regex '.*/(Cargo\.toml|Cargo\.lock)' ! -regex '.*/src/(lib|main)\.rs' -delete \
    && find . -depth -type d -empty -delete \
    && for root in $(find . -path '*/src/lib.rs' -o -path '*/src/main.rs'); do \
        printf '//! Dependency stub.\n' > "${root}"; \
        if test "${root##*/}" = main.rs; then printf 'fn main() {}\n' >> "${root}"; fi; \
    done

# The builder's Debian 13 (trixie) glibc matches the distroless cc-debian13 runtime the binary runs on. Every
# dependency is compiled here with the release profile, pinned by backend/Cargo.lock; the stub packages' artifacts are
# then removed, so the real sources always compile.
FROM docker.io/library/rust:1.99.0-trixie@sha256:6ff07edce8775d0f64be7aba9197229407301bddf2054d62c27b541a6238a181 AS rust-dependencies
WORKDIR /workspace
COPY --from=rust-skeleton /workspace ./
RUN cd backend \
    && cargo build --release --locked --bin shimpz-store \
    && cargo clean --release --locked --package store-backend --package strict-json --package team-protocol

FROM rust-dependencies AS rust-build
COPY backend/Cargo.toml backend/Cargo.lock ./backend/
COPY backend/src ./backend/src
COPY vendor/strict-json ./vendor/strict-json
COPY protocol/team/http ./protocol/team/http
ARG SOURCE_DATE_EPOCH=0
RUN cd backend && cargo build --release --locked --bin shimpz-store

# One root-owned binary and the root-owned prerendered build; the runtime identity can modify neither, and the root
# filesystem is read-only anyway. uid 10008 needs no passwd entry. The healthcheck subcommand needs no shell.
FROM gcr.io/distroless/cc-debian13@sha256:ed7c407fd64eb0af9dddb9456b94cee188a40a7f53cf38c9836e1e9ae14fca02 AS runtime
COPY --link --from=rust-build --chmod=0555 /workspace/backend/target/release/shimpz-store /usr/local/bin/shimpz-store
COPY --link --from=web /w/build /app/build
USER 10008:10008
EXPOSE 3200
ENTRYPOINT ["/usr/local/bin/shimpz-store"]
