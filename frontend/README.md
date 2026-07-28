# Shimpz Store frontend

This SvelteKit application renders the public Store and the Assistant Store embedded by the local
Admin. The production build is static and is served by the Store backend.

Use Node.js 24 and the lockfile-pinned pnpm release from this directory:

```sh
corepack pnpm@11.9.0 install --frozen-lockfile
corepack pnpm@11.9.0 test
corepack pnpm@11.9.0 check
corepack pnpm@11.9.0 build
```

`test` runs the frontend contracts with half of the host processors. `check` validates the Svelte
application, and `build` produces the static files copied into the production image. Run
`corepack pnpm@11.9.0 dev` only for local development.

Rendered navigation, responsive behavior, and the Admin-to-Store handshake are covered by the
umbrella repository's Playwright suite against built applications.
