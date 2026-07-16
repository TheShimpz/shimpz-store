import { error } from "@sveltejs/kit";
import {
  ASSISTANT_BY_ID,
  ASSISTANT_CATALOG,
  LOCALES,
  type AssistantListing,
  type Locale,
} from "$lib/catalog";

export const prerender = true;

export function entries() {
  const out: { lang: string; id: string }[] = [];
  for (const lang of LOCALES) {
    for (const assistant of ASSISTANT_CATALOG) out.push({ lang, id: assistant.id });
  }
  return out;
}

export function load({ params }: { params: { lang: string; id: string } }) {
  const assistant = ASSISTANT_BY_ID.get(params.id);
  if (!assistant) error(404, "Assistant not found");
  return { lang: params.lang as Locale, assistant: assistant as AssistantListing };
}
