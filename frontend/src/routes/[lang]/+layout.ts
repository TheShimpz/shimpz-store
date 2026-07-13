import { error } from "@sveltejs/kit";
import { LOCALES, type Locale } from "$lib/catalog";

export const prerender = true;

export function load({ params }: { params: { lang: string } }) {
  if (!LOCALES.includes(params.lang as Locale)) error(404, "unknown language");
  return { lang: params.lang as Locale };
}
