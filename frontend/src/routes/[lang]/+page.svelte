<script lang="ts">
  import { ShimpzBrand } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import HomepageMeshBackground from "$lib/components/HomepageMeshBackground.svelte";
  import HomepageVideo from "$lib/components/HomepageVideo.svelte";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { homepage } from "$lib/homepage";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(homepage(lang));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet brandSymbol(slot = "homepage-brand-monument")}
  <div class="hero-brand" data-slot={slot}>
    <ShimpzBrand variant="symbol" decorative />
  </div>
{/snippet}

<div class="homepage-shell">
  <HomepageMeshBackground />
  <div class="homepage-content" data-slot="homepage-content">
    <div class="evidence-band" data-slot="homepage-evidence-band">
      <div class="editorial-wrap evidence-section">
        <div class="evidence-install-row">
          {@render brandSymbol("homepage-install-brand")}
          <div class="evidence-install-content">
            <ul class="hero-differentials" data-slot="homepage-differentials" role="list">
              <li><a href={u.openSource(lang)}><span aria-hidden="true">//</span>{tr("nav_open_source", lang)}</a></li>
              <li><a href={u.security(lang)}><span aria-hidden="true">//</span>{tr("nav_security", lang)}</a></li>
            </ul>
            <div data-slot="homepage-install-command"><InstallCommand {lang} /></div>
          </div>
        </div>
      </div>
    </div>

    <div class="editorial-wrap hero-space">
      <section data-slot="editorial-hero" class="homepage-hero">
        <header>
          <h1 id="hero-title" class="glitch-title" data-text={content.title}>
            {#if lang === "en"}<span class="title-accent">I do the work</span>{" "}<span>so you can focus on what matters.</span>{:else}{content.title}{/if}
          </h1>
        </header>
        <div class="body">
          <div class="copy">
            <div data-slot="editorial-hero-actions" class="actions">
              <HomepageVideo />
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</div>

<style>
  .homepage-shell { position: relative; isolation: isolate; }
  .homepage-content { position: relative; z-index: 1; }
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space { padding-block: clamp(2.5rem, 5vw, 4.5rem); }
  .homepage-hero {
    --shimpz-type-display-size: clamp(2.15rem, 3.4vw, 3.5rem);
    --shimpz-type-display-measure: 30ch;
    display: grid;
    justify-items: center;
    row-gap: var(--shimpz-space-4);
    text-align: center;
  }
  .homepage-hero > header,
  .homepage-hero > .body { width: min(100%, 47rem); min-width: 0; }
  h1 {
    position: relative;
    max-inline-size: var(--shimpz-type-display-measure);
    margin: 0 auto;
    color: var(--color-fg);
    font: 680 var(--shimpz-type-display-size)/var(--shimpz-type-display-leading) var(--font-sans);
    letter-spacing: var(--shimpz-type-display-tracking);
    text-wrap: balance;
  }
  .title-accent { color: var(--color-cyan); }
  .glitch-title::before,
  .glitch-title::after {
    content: attr(data-text);
    position: absolute;
    inset: 0;
    color: var(--color-fg);
    opacity: 0;
    pointer-events: none;
  }
  .glitch-title::before {
    animation: glitch-cyan 4.8s infinite steps(1, end);
    text-shadow: -3px 0 var(--color-cyan);
  }
  .glitch-title::after {
    animation: glitch-pink 4.8s 70ms infinite steps(1, end);
    text-shadow: 3px 0 var(--color-pink);
  }
  .body,
  .copy { min-width: 0; }
  .actions { display: flex; justify-content: center; }
  .evidence-section { padding-block: clamp(2rem, 4vw, 3.5rem); }
  .evidence-install-row {
    display: grid;
    grid-template-columns: auto minmax(0, 44rem);
    align-items: center;
    justify-content: center;
    width: min(100%, 58rem);
    margin-inline: auto;
    gap: clamp(1rem, 2vw, 1.5rem);
  }
  .evidence-install-content { display: grid; min-width: 0; gap: var(--shimpz-space-4); }
  .hero-differentials {
    display: flex;
    flex-wrap: wrap;
    gap: var(--shimpz-space-4) var(--shimpz-space-6);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .hero-differentials a {
    display: inline-flex;
    align-items: center;
    gap: var(--shimpz-space-2);
    color: var(--color-fg);
    font: 600 0.72rem/1.2 var(--font-mono);
    letter-spacing: 0.08em;
    text-decoration: none;
    text-transform: uppercase;
  }
  .hero-differentials a:hover,
  .hero-differentials a:focus-visible { color: var(--color-cyan); }
  .hero-differentials span { color: var(--color-cyan); font-size: 0.62rem; }
  .hero-brand {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .hero-brand :global([data-slot="shimpz-brand-mark"]) {
    width: clamp(7.5rem, 12vw, 10rem);
    height: clamp(7.5rem, 12vw, 10rem);
  }
  .evidence-band { background: transparent; }
  :global(body:has(.homepage-shell) button),
  :global(body:has(.homepage-shell) .shimpz-action-link) {
    animation: button-glitch 4.8s 140ms infinite steps(1, end);
  }
  @media (max-width: 900px) {
    .homepage-hero {
      --shimpz-type-display-size: clamp(1.65rem, 6.9vw, 2rem);
      --shimpz-type-display-measure: 22ch;
    }
  }
  @media (max-width: 620px) {
    .evidence-install-row { grid-template-columns: 1fr; }
  }
  @keyframes glitch-cyan {
    0%, 86%, 91%, 100% { opacity: 0; transform: translate(0); clip-path: inset(0); }
    87% { opacity: 0.72; transform: translate(-3px, 1px); clip-path: inset(12% 0 64% 0); }
    88% { opacity: 0.55; transform: translate(2px, -1px); clip-path: inset(56% 0 18% 0); }
    89% { opacity: 0.7; transform: translate(-1px, 0); clip-path: inset(32% 0 42% 0); }
  }
  @keyframes glitch-pink {
    0%, 87%, 92%, 100% { opacity: 0; transform: translate(0); clip-path: inset(0); }
    88% { opacity: 0.62; transform: translate(3px, -1px); clip-path: inset(64% 0 10% 0); }
    89% { opacity: 0.5; transform: translate(-2px, 1px); clip-path: inset(18% 0 58% 0); }
    90% { opacity: 0.66; transform: translate(1px, 0); clip-path: inset(43% 0 31% 0); }
  }
  @keyframes button-glitch {
    0%, 86%, 91%, 100% { transform: translate(0); filter: none; }
    87% { transform: translate(-2px, 1px); filter: drop-shadow(2px 0 var(--color-pink)); }
    88% { transform: translate(2px, -1px); filter: drop-shadow(-2px 0 var(--color-cyan)); }
    89% { transform: translate(-1px, 0); filter: drop-shadow(1px 0 var(--color-pink)); }
  }
  @media (prefers-reduced-motion: reduce) {
    .glitch-title::before,
    .glitch-title::after,
    :global(body:has(.homepage-shell) button),
    :global(body:has(.homepage-shell) .shimpz-action-link) { animation: none; }
  }
  @media (forced-colors: active) {
    h1,
    .title-accent { color: CanvasText; }
  }
</style>
