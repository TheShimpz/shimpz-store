# Store repository rules

## Authority

- This repository owns the public institutional site, public Assistant discovery, and the Store surface embedded
  by Local Admin. It retains authenticated Hosted orchestration APIs, but exposes no public Account, login, Team,
  or chat pages.
- Store projects Developers data and sends exact install intent to Team. It does not own publication, catalog
  admission, Team lifecycle, Account identity, model-provider credential custody, or installation authority.
- `egress/` owns only the dedicated Hosted Store-to-Neuron CONNECT enforcement and audit boundary. Store remains
  absent from direct outbound networks, and the proxy never receives OAuth or Cloudflare Access credentials.
- Read the canonical [Shimpz architecture](https://github.com/TheShimpz/shimpz/blob/main/.context/ARCHITECTURE.md)
  before changing product vocabulary, authority, protocols, runtime topology, or source placement.

## Delivery and engineering

- Deliver the smallest useful microtask, validate it, commit it with a clear English conventional message, and
  push it immediately.
- When working through the umbrella checkout, commit and push this repository before committing its umbrella
  gitlink.
- Shimpz is pre-production. Change the current contract directly; do not add compatibility routes, old schemas,
  mutable install fallbacks, or earlier repository-state cleanup.
- Preserve Account and Team isolation, no Docker socket, exact source digests, non-cacheable private data,
  file-backed capabilities, strict WebSocket frames, and secret redaction.
- Use Python 3.14 and Node.js 24. User-visible Svelte behavior requires Playwright against the built application.
- Tests that support workers use half of local processors and all GitHub Actions runner processors. Do not add
  Cypress or an experimental component-test runner.

## Validation

- Run `ruff check --config ruff.toml .`.
- Run backend tests from `backend/` with
  `DATABASE_URL=postgresql+psycopg://ci:ci@127.0.0.1:9/ci SECRET_KEY=ci-only-not-a-secret uv run --python 3.14
  --locked --with httpx2==2.5.0 --with python-multipart==0.0.32 --with coverage==7.15.2 sh -c "coverage run
  --branch --source=app -m pytest -q tests && coverage report --skip-empty --fail-under=79"`.
- Run frontend tests/check/build from `frontend/` with the pinned pnpm release.
