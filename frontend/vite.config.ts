import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";

// Dev only: proxy the relative /api calls (and the /ws websocket) to the local backend so the SAME
// code runs in dev and live (in production Caddy routes /api/* and /ws). These loopbacks live in
// the dev config, NEVER in src/.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiPort = env.SHIMPZ_API_PORT || "8000";
  const wsPort = env.SHIMPZ_WS_PORT || "8001";
  return {
    plugins: [tailwindcss(), sveltekit()],
    server: {
      proxy: {
        "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true },
        "/ws": { target: `ws://127.0.0.1:${wsPort}`, ws: true },
      },
    },
  };
});
