# Shimpz Store

Shimpz Store owns the institutional website, public Assistant discovery, and the platform Cloudflare OAuth broker.
Its public SvelteKit frontend exposes the homepage, Assistant catalog and disclosures, institutional footer pages,
and the branded not-found experience. It exposes no Account, login, Team, chat, model-provider, or
Assistant-installation API or page.

The FastAPI backend projects the public Developers catalog and its icons, serves the prerendered site, and brokers
Cloudflare OAuth for Local Spaces. It starts with only Developers and its OAuth secrets. Store is an unprivileged
gateway, not publication, Account, Team, or installation authority; it has no Docker socket, provider admin key, or
Team bearer.

## Security boundary

- Public catalog and icon responses are projected from Developers; Store never admits a publication or substitutes a
  mutable artifact identity.
- Every page refuses framing. Local Admin lists the catalog natively and sends Team only an exact Assistant ID and
  source digest; Team independently authorizes, resolves, verifies, binds, and runs that publication.
- OAuth uses PKCE and an audited broker; provider credentials never enter URLs, browser-readable state, or logs.
  The broker returns to the Local Admin only by a closed callback mode: `loopback`, `local-domain`, or `out-of-band`.
- Static files resolve beneath the built application root; unknown API paths do not fall through to the
  SPA, and private JSON responses are non-cacheable.

The production image runs non-root with a read-only filesystem, fixed dependency locks, and only the
compiled frontend plus explicitly copied backend modules. Backend and frontend contracts live under
their respective `tests/` directories; built-browser behavior is exercised from the umbrella repository.

## Frontend commands

Use Node.js 24 and the lockfile-pinned pnpm release:

```sh
cd frontend
corepack pnpm@11.9.0 install --frozen-lockfile --ignore-scripts
corepack pnpm@11.9.0 test
corepack pnpm@11.9.0 check
corepack pnpm@11.9.0 build
```

`test` runs the dependency-free frontend contracts with half of the host processors. `check` validates
the Svelte application, and `build` produces the static application consumed by the FastAPI image.
