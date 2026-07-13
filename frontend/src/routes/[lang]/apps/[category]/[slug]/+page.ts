import { error } from "@sveltejs/kit";
import { LOCALES, APPS, APP_BY_ID, catSlug, type Locale } from "$lib/catalog";

export const prerender = true;

export function entries() {
  const out: { lang: string; category: string; slug: string }[] = [];
  for (const lang of LOCALES) for (const a of APPS) out.push({ lang, category: catSlug(a.category), slug: a.id });
  return out;
}

export function load({ params }: { params: { lang: string; category: string; slug: string } }) {
  const a = APP_BY_ID.get(params.slug);
  if (!a || catSlug(a.category) !== params.category) error(404, "app not found");
  return { lang: params.lang as Locale, app: a };
}
