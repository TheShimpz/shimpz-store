import { LOCALES } from "$lib/locales";

export const prerender = true;

export function entries() {
  return LOCALES.map((lang) => ({ lang }));
}
