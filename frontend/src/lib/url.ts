// Public URLs for the implemented product surfaces.
import type { Locale } from "$lib/locales";

export const SITE = "https://shimpz.com";

export const u = {
  home: (l: Locale) => `/${l}`,
  assistants: (l: Locale) => `/${l}/assistants`,
  openSource: (l: Locale) => `/${l}/open-source`,
  about: (l: Locale) => `/${l}/about`,
};

// Same page in another locale — swaps the leading /<lang>/ segment (for hreflang + the language switch).
export const swapLocale = (path: string, target: Locale): string =>
  /^\/[a-z]{2}(\/|$)/.test(path)
    ? path.replace(/^\/[a-z]{2}(\/|$)/, `/${target}$1`)
    : u.home(target);
