<script lang="ts">
  import type { Snippet } from "svelte";
  import SiteFooter from "$lib/components/SiteFooter.svelte";
  import SiteHeader from "$lib/components/SiteHeader.svelte";
  import { SITE } from "$lib/url";

  let {
    title,
    path,
    description,
    effectiveDate,
    children,
  }: {
    title: string;
    path: "/privacy" | "/terms";
    description: string;
    effectiveDate: string;
    children: Snippet;
  } = $props();

  const canonical = $derived(`${SITE}${path}`);
</script>

<svelte:head>
  <title>{title} — Shimpz</title>
  <meta name="description" content={description} />
  <meta name="robots" content="index,follow" />
  <link rel="canonical" href={canonical} />
  <meta property="og:title" content={`${title} — Shimpz`} />
  <meta property="og:description" content={description} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonical} />
  <meta property="og:site_name" content="Shimpz" />
</svelte:head>

<SiteHeader lang="en" {path} />

<main id="main-content" tabindex="-1" class="wrap legal-shell">
  <header class="legal-title">
    <p class="kicker">Legal</p>
    <h1>{title}</h1>
    <p class="description">{description}</p>
    <p class="effective">Effective {effectiveDate}</p>
  </header>

  <article class="legal-content">
    {@render children()}
  </article>
</main>

<SiteFooter lang="en" />

<style>
  .legal-shell { width: min(100% - 2rem, 800px); }

  .legal-title {
    padding-block: clamp(4rem, 9vw, 7rem) clamp(2.5rem, 6vw, 4rem);
    border-bottom: 1px solid var(--color-border);
  }

  .legal-title h1 {
    max-width: 13ch;
    margin: 0.75rem 0 1.25rem;
    font-size: clamp(2.4rem, 7vw, 4.8rem);
    line-height: 0.98;
  }

  .description {
    max-width: 60ch;
    margin: 0;
    color: var(--color-muted);
    font-size: 1.08rem;
  }

  .effective {
    margin: 1.5rem 0 0;
    color: var(--color-muted-2);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .legal-content { padding-block: 3rem; }
  .legal-content :global(section) { margin-bottom: 3rem; }
  .legal-content :global(h2) {
    margin: 0 0 1rem;
    color: var(--color-fg);
    font-size: clamp(1.25rem, 3vw, 1.65rem);
    line-height: 1.25;
  }
  .legal-content :global(p),
  .legal-content :global(li) { color: var(--color-muted); }
  .legal-content :global(p) { margin: 0 0 1rem; }
  .legal-content :global(ul) { margin: 0; padding-inline-start: 1.25rem; }
  .legal-content :global(li) { margin-block-end: 0.6rem; padding-inline-start: 0.25rem; }
  .legal-content :global(strong) { color: var(--color-fg); }
  .legal-content :global(a) {
    color: var(--color-cyan);
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }
</style>
