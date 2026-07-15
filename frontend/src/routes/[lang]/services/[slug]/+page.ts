import { error } from "@sveltejs/kit";
import { LOCALES, SERVICES, SERVICE_BY_ID, type Locale } from "$lib/catalog";

export const prerender = true;

export function entries() {
  const out: { lang: string; slug: string }[] = [];
  for (const lang of LOCALES) for (const service of SERVICES) out.push({ lang, slug: service.id });
  return out;
}

export function load({ params }: { params: { lang: string; slug: string } }) {
  const service = SERVICE_BY_ID.get(params.slug);
  if (!service) error(404, "service not found");
  return { lang: params.lang as Locale, service };
}
