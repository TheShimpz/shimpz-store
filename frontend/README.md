# Shimpz Store frontend

This SvelteKit application renders the public Store. The production build is static and is served by the Store
backend.

Use Node.js 26 and the exact pnpm release `bootstrap-pnpm.sh` installs from its hash-pinned registry tarball (Node.js 26
bundles no Corepack), from this directory:

```sh
sh bootstrap-pnpm.sh /tmp/pnpm-cache /tmp/pnpm
export PATH="/tmp/pnpm/bin:$PATH"
pnpm install --frozen-lockfile --ignore-scripts
pnpm test
pnpm check
pnpm build
```

`test` runs the frontend contracts with half of the host processors. `check` validates the Svelte
application, and `build` produces the static files copied into the production image. Run
`pnpm dev` only for local development.

Rendered navigation, responsive behavior, and the Admin-to-Store handshake are covered by the
umbrella repository's Playwright suite against built applications.
