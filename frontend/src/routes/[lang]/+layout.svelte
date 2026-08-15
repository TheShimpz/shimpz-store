<script lang="ts">
  import { browser } from "$app/environment";
  import { page } from "$app/stores";
  import type { Locale } from "$lib/catalog";
  import SiteFooter from "$lib/components/SiteFooter.svelte";
  import SiteHeader from "$lib/components/SiteHeader.svelte";
  import { tr } from "$lib/i18n";
  import { localeDirection } from "$lib/locales";

  let { data, children } = $props();
  const lang = $derived(data.lang as Locale);
  const pathname = $derived($page.url.pathname);
  const path = $derived(pathname + (browser ? $page.url.search : ""));
  const embedded = $derived(pathname.replace(/\/$/, "") === `/${lang}/assistants/embed`);
  const home = $derived(pathname.replace(/\/$/, "") === `/${lang}`);

  $effect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = localeDirection(lang);
  });
</script>

{#if !embedded}<SiteHeader {lang} {path} />{/if}

<main id="main-content" tabindex="-1" class:embedded>
  {@render children()}
</main>

{#if !embedded}<SiteFooter {lang} statement={home ? tr("home_privacy_line", lang) : undefined} />{/if}

<style>
  main { min-height: calc(100vh - 12rem); }
  main.embedded { min-height: 100vh; padding-bottom: 2rem; }
</style>
