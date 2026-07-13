import { redirect } from "@sveltejs/kit";

export const prerender = true;

// Root → the default English locale. hreflang covers pt; the language switch lives in the header.
export function load() {
  redirect(308, "/en");
}
