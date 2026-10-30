# Store repository rules

## Authority

- This repository owns the platform's public institutional site, public Assistant discovery, and the platform OAuth
  broker. It exposes no Account, login, Team, chat, or orchestration API or page, and no page may be framed.
- Store projects Developers data. It does not own publication, catalog admission, Team lifecycle, Account identity,
  or installation authority.
- `egress/` owns only the dedicated platform Store-to-Neuron CONNECT enforcement and audit boundary. Store remains
  absent from direct outbound networks, and the proxy never receives OAuth or Cloudflare Access credentials.
- Read the canonical [Shimpz architecture](https://github.com/TheShimpz/shimpz/blob/main/.context/ARCHITECTURE.md)
  before changing product vocabulary, authority, protocols, runtime topology, or source placement.

## Delivery and engineering

- Deliver the smallest useful microtask, validate it, and commit it with a clear English conventional message.
- Commits reach `main` only through the umbrella's `.scripts/local-release/deploy` (ADR-0102), which pushes this
  repository's commits before the umbrella commit that records their gitlink. Never push around it.
- Shimpz is pre-production. Change the current contract directly; do not add compatibility routes, old schemas,
  mutable install fallbacks, or earlier repository-state cleanup.
- Preserve no Docker socket, exact source digests, non-cacheable private data, file-backed capabilities, and secret
  redaction.
- The backend is the Rust package `backend/` (ADR-0123); use Node.js 26 for every Node.js workload this repository
  runs. User-visible Svelte behavior requires Playwright against the built application.
- Tests that support workers use half of local processors and all GitHub Actions runner processors. Do not add
  Cypress or an experimental component-test runner.

## Validation

- From the umbrella root, run `.scripts/gate/rust crate store/backend` for the backend (fmt, clippy pedantic,
  cargo-deny, its tests, and its fuzz targets) and `.scripts/gate/live store-contract`
  for the black-box contract of the built image. The vendored strict-JSON and Team-protocol mirrors are proven by
  their producers and byte-identity checks.
- Run frontend tests/check/build from `frontend/` with the pnpm release `frontend/bootstrap-pnpm.sh` installs.
- `egress/` is a Rust package built with the umbrella `.egress/transport` crate; from the umbrella root run
  `.scripts/gate/rust crate store/egress`.
