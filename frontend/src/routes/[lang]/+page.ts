import { LOCALES } from "#lib/locales.js";

export const prerender = true;

export function entries() {
  return LOCALES.map((lang) => ({ lang }));
}
