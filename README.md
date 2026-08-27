# Shimpz Store

Shimpz Store owns the institutional website, public Assistant discovery, and the catalog surface embedded by Local
Admin. Its public SvelteKit frontend exposes the homepage, Assistant catalog and disclosures, institutional footer
pages, and the branded not-found experience. It exposes no public Account, login, Team, chat, model-provider setup,
or Hosted Assistant-installation page.

The FastAPI backend projects the public Developers catalog and retains authenticated Hosted orchestration APIs for
Account, Team, files, inference, Assistant lifecycle, OAuth, and `shimpz.chat.v7`. No current public Store browser
surface consumes those retained application APIs. Store is an unprivileged gateway, not publication, Account, Team,
or installation authority; it has no Docker socket, provider admin key, or Team bearer.

## Security boundary

- Public catalog and icon responses are projected from Developers; Store never admits a publication or substitutes a
  mutable artifact identity.
- Local Admin's embedded catalog sends only an exact Assistant ID and source digest. Team independently authorizes,
  resolves, verifies, binds, and runs that publication.
- Retained Hosted APIs verify secure, HTTP-only, same-site Account sessions before protected work. Team IDs bind the
  complete Account ID and normalized Team name with a collision-resistant digest.
- OAuth uses PKCE and an audited broker; provider credentials never enter URLs, browser-readable state,
  logs, or controller chat frames.
- The retained Chat v5 backend accepts only bounded messages, opaque file IDs, and selected installed Assistant IDs,
  and emits only exact admitted frames.
- Static files resolve beneath the built application root; unknown API paths do not fall through to the
  SPA, and private JSON responses are non-cacheable.

The production image runs non-root with a read-only filesystem, fixed dependency locks, and only the
compiled frontend plus explicitly copied backend modules. Backend and frontend contracts live under
their respective `tests/` directories; built-browser behavior is exercised from the umbrella repository.

## Frontend commands

Use Node.js 24 and the lockfile-pinned pnpm release:

```sh
cd frontend
corepack pnpm@11.9.0 install --frozen-lockfile
corepack pnpm@11.9.0 test
corepack pnpm@11.9.0 check
corepack pnpm@11.9.0 build
```

`test` runs the dependency-free frontend contracts with half of the host processors. `check` validates
the Svelte application, and `build` produces the static application consumed by the FastAPI image.
