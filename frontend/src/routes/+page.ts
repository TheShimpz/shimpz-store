import { redirect } from "@sveltejs/kit";

export const prerender = true;

// Root → the default English locale; Seo emits alternates for every supported locale.
export function load() {
  redirect(308, "/en");
}
