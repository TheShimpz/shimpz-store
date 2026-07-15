import { redirect } from "@sveltejs/kit";
import { LOCALES, type Locale } from "$lib/catalog";
import { u } from "$lib/url";

export const prerender = true;

export function entries() {
  return LOCALES.map((lang) => ({ lang }));
}

export function load({ params }: { params: { lang: string } }) {
  redirect(308, u.services(params.lang as Locale));
}
