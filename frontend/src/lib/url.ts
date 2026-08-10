// Public URLs for the implemented product and platform-capability surfaces.
import type { Locale, Service } from "$lib/catalog";

export const SITE = "https://shimpz.com";

export const u = {
  home: (l: Locale) => `/${l}`,
  services: (l: Locale) => `/${l}/services`,
  service: (l: Locale, service: Service) => `/${l}/services/${service.id}`,
  assistants: (l: Locale) => `/${l}/assistants`,
  team: (l: Locale) => `/${l}/team`,
  chat: (l: Locale, teamId?: string) =>
    `/${l}/chat${teamId ? `?team=${encodeURIComponent(teamId)}` : ""}`,
  login: (l: Locale) => `/${l}/login`,
  account: (l: Locale) => `/${l}/account`,
  creators: (l: Locale) => `/${l}/creators`,
  creator: (l: Locale, handle: string) => `/${l}/creators/${handle}`,
};

// Same page in another locale — swaps the leading /<lang>/ segment (for hreflang + the language switch).
export const swapLocale = (path: string, target: Locale): string =>
  /^\/[a-z]{2}(\/|$)/.test(path)
    ? path.replace(/^\/[a-z]{2}(\/|$)/, `/${target}$1`)
    : u.home(target);
