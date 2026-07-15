import type { Handle } from "@sveltejs/kit";

export const handle: Handle = async ({ event, resolve }) => {
  const routeLanguage = event.url.pathname.split("/")[1];
  const language = routeLanguage === "pt" ? "pt" : "en";

  return resolve(event, {
    transformPageChunk: ({ html }) => html.replace("%lang%", language),
  });
};
