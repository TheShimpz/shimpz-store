import type { Handle } from "@sveltejs/kit";
import { isLocale, localeDirection } from "$lib/locales";

export const handle: Handle = async ({ event, resolve }) => {
  const routeLanguage = event.url.pathname.split("/")[1];
  const language = isLocale(routeLanguage) ? routeLanguage : "en";
  const direction = localeDirection(language);

  return resolve(event, {
    transformPageChunk: ({ html }) => html
      .replaceAll("%lang%", language)
      .replaceAll("%dir%", direction),
  });
};
