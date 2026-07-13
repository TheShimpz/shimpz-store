import { error } from "@sveltejs/kit";
import {
  LOCALES, APP_CATEGORIES, usedCategories, appsInCategory, catSlug,
  type Locale, type AppCategory,
} from "$lib/catalog";

export const prerender = true;

export function entries() {
  const out: { lang: string; category: string }[] = [];
  for (const lang of LOCALES) for (const cat of usedCategories()) out.push({ lang, category: catSlug(cat) });
  return out;
}

export function load({ params }: { params: { lang: string; category: string } }) {
  const cat = APP_CATEGORIES.find((c) => catSlug(c) === params.category) as AppCategory | undefined;
  if (!cat) error(404, "unknown category");
  return { lang: params.lang as Locale, category: cat, apps: appsInCategory(cat) };
}
