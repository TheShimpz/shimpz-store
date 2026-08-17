import { LOCALES } from "$lib/locales";

export const prerender = true;
export const csr = false;

export function entries() {
  return LOCALES.map((lang) => ({ lang }));
}
