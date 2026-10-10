import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";

// Dev only: proxy relative /api calls, including the canonical Team chat WebSocket, to the local
// backend. The same paths run in production through Caddy; loopbacks never enter src/.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiPort = env.SHIMPZ_API_PORT || "8000";
  return {
    plugins: [
      tailwindcss(),
      // Static public product and team documentation; authenticated Team operations stay under /api.
      sveltekit({
        preprocess: vitePreprocess(),
        adapter: adapter({ strict: false }),
        version: { name: process.env.SOURCE_DATE_EPOCH || "0", pollInterval: 0 },
      }),
    ],
    server: {
      proxy: {
        "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true, ws: true },
      },
    },
  };
});
