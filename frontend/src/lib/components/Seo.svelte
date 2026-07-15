<script lang="ts">
  import { page } from "$app/stores";
  import { LOCALES, type Locale } from "$lib/catalog";
  import { SITE, swapLocale } from "$lib/url";

  let { title, description, lang }: { title: string; description: string; lang: Locale } = $props();

  const path = $derived($page.url.pathname);
  const canonical = $derived(SITE + path);
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={canonical} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonical} />
  <meta property="og:site_name" content="Shimpz" />
  <meta property="og:image" content={`${SITE}/brand/shimpz-cyberchimp.png`} />
  <meta property="og:image:width" content="1254" />
  <meta property="og:image:height" content="1254" />
  <meta property="og:image:alt" content="Shimpz cyberchimp symbol" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image" content={`${SITE}/brand/shimpz-cyberchimp.png`} />
  <meta property="og:locale" content={lang} />
  {#each LOCALES as l (l)}
    <link rel="alternate" hreflang={l} href={SITE + swapLocale(path, l as Locale)} />
  {/each}
  <link rel="alternate" hreflang="x-default" href={SITE + swapLocale(path, "en")} />
</svelte:head>
