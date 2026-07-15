<script lang="ts">
  import { page } from "$app/stores";
  import type { Locale } from "$lib/catalog";
  import SiteFooter from "$lib/components/SiteFooter.svelte";
  import SiteHeader from "$lib/components/SiteHeader.svelte";

  let { data, children } = $props();
  const lang = $derived(data.lang as Locale);
  const path = $derived($page.url.pathname);
</script>

<SiteHeader {lang} {path} />

<main id="main-content">
  {@render children()}
</main>

<SiteFooter {lang} />

<style>
  main { min-height: calc(100vh - 12rem); }
</style>
