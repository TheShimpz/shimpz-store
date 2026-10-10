<script lang="ts">
  import { browser } from "$app/env";
  import { page } from "$app/state";
  import type { Locale } from "#lib/locales.js";
  import SiteFooter from "#lib/components/SiteFooter.svelte";
  import SiteHeader from "#lib/components/SiteHeader.svelte";
  import { tr } from "#lib/i18n.js";
  import { localeDirection } from "#lib/locales.js";

  let { data, children } = $props();
  const lang = $derived(data.lang as Locale);
  const pathname = $derived(page.url.pathname);
  const path = $derived(pathname + (browser ? page.url.search : ""));
  const home = $derived(pathname.replace(/\/$/, "") === `/${lang}`);

  $effect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = localeDirection(lang);
  });
</script>

<SiteHeader {lang} {path} />

<main id="main-content" tabindex="-1">
  {@render children()}
</main>

<SiteFooter {lang} statement={home ? tr("home_privacy_line", lang) : undefined} />

<style>
  main { min-height: calc(100vh - 12rem); }
</style>
