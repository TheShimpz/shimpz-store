<script lang="ts">
  import type { Locale } from "$lib/catalog";
  import HomepageMeshBackground from "$lib/components/HomepageMeshBackground.svelte";
  import HomepageVideo from "$lib/components/HomepageVideo.svelte";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { homepage } from "$lib/homepage";
  import { tr } from "$lib/i18n";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(homepage(lang));
  const titleSeparator = $derived(lang === "zh" || lang === "ja" ? "" : " ");
  const titleLines = $derived([
    `${content.title.accent}${content.title.remainder ? `${titleSeparator}${content.title.remainder}` : ""}`,
    content.title.secondLine,
  ] as const);
  const titleText = $derived(titleLines.join(titleSeparator));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

<div class="homepage-shell">
  <HomepageMeshBackground />
  <div class="homepage-content" data-slot="homepage-content">
    <div class="editorial-wrap hero-space">
      <section data-slot="editorial-hero" lang={lang} class="homepage-hero">
        <header>
          <h1 id="hero-title" class="glitch-title" data-text={titleLines.join("\n")} aria-label={titleText}>
            <span class="headline-line"><span class="title-accent">{content.title.accent}</span>{#if content.title.remainder}{titleSeparator}{content.title.remainder}{/if}</span>
            <span class="headline-line">{content.title.secondLine}</span>
          </h1>
          <p class="hero-privacy">{tr("home_privacy_line", lang)}</p>
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

    <div class="evidence-band" data-slot="homepage-evidence-band">
      <div class="editorial-wrap evidence-section">
        <div class="evidence-install-row">
          <div class="evidence-install-content">
            <ul class="hero-differentials" data-slot="homepage-differentials" role="list">
              <li><span aria-hidden="true">//</span>{tr("nav_open_source", lang)}</li>
              <li><span aria-hidden="true">//</span>{tr("home_self_hosted", lang)}</li>
              <li><span aria-hidden="true">//</span>{tr("home_sandboxed", lang)}</li>
            </ul>
            <div data-slot="homepage-install-command"><InstallCommand {lang} /></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .homepage-shell { position: relative; isolation: isolate; }
  .homepage-content { position: relative; z-index: 1; }
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space {
    padding-block-start: clamp(3rem, 5vw, 5rem);
  }
  .homepage-hero {
    --shimpz-type-display-size: clamp(2.15rem, 3.4vw, 3.5rem);
    --shimpz-type-display-measure: 30ch;
    display: grid;
    justify-items: center;
    row-gap: clamp(3rem, 5vw, 5rem);
    text-align: center;
  }
  .homepage-hero > header { position: relative; width: min(100%, 64rem); min-width: 0; }
  .homepage-hero > .body { width: min(100%, 47rem); min-width: 0; }
  h1 {
    position: relative;
    margin: 0 auto;
    color: var(--color-fg);
    font: 680 var(--shimpz-type-display-size)/var(--shimpz-type-display-leading) var(--font-sans);
    letter-spacing: var(--shimpz-type-display-tracking);
    text-wrap: balance;
  }
  .headline-line { display: block; white-space: nowrap; }
  .hero-privacy {
    position: absolute;
    inset-block-start: calc(100% + var(--shimpz-space-2));
    inset-inline: 0;
    margin: 0;
    color: var(--color-muted);
    font: 500 calc(var(--shimpz-type-display-size) * 0.4)/1.3 var(--font-sans);
    text-align: center;
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
    white-space: pre;
  }
  .glitch-title::before {
    animation: glitch-cyan 4.8s infinite steps(1, end);
    text-shadow: -3px 0 var(--color-cyan);
  }
  .glitch-title::after {
    animation: glitch-pink 4.8s 70ms infinite steps(1, end);
    text-shadow: 3px 0 var(--color-magenta);
  }
  .body,
  .copy { min-width: 0; }
  .actions { display: flex; justify-content: center; }
  .evidence-section {
    padding-block: clamp(3rem, 5vw, 5rem) clamp(1rem, 2vw, 1.5rem);
  }
  .evidence-install-row {
    display: grid;
    grid-template-columns: minmax(0, 35.2rem);
    align-items: center;
    justify-content: center;
    width: min(100%, 35.2rem);
    margin-inline: auto;
  }
  .evidence-install-content { display: grid; min-width: 0; gap: var(--shimpz-space-4); }
  .hero-differentials {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--shimpz-space-4) var(--shimpz-space-6);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .hero-differentials li {
    display: inline-flex;
    align-items: center;
    gap: var(--shimpz-space-2);
    color: var(--color-fg);
    font: 600 0.72rem/1.2 var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .hero-differentials span { color: var(--color-cyan); font-size: 0.62rem; }
  :global([dir="rtl"]) .hero-differentials li { letter-spacing: normal; }
  .evidence-band { background: transparent; }
  @media (max-width: 900px) {
    .homepage-hero {
      --shimpz-type-display-size: clamp(1.65rem, 6.9vw, 2rem);
      --shimpz-type-display-measure: 22ch;
    }
  }
  @media (max-width: 620px) {
    .homepage-hero { --shimpz-type-display-size: clamp(1rem, 7vw, 3.3rem); }
    .homepage-hero:lang(pt),
    .homepage-hero:lang(es) { --shimpz-type-display-size: clamp(1rem, 5.6vw, 3.3rem); }
    .homepage-hero:lang(fr) { --shimpz-type-display-size: clamp(1rem, 5.2vw, 3.3rem); }
    .homepage-hero:lang(de),
    .homepage-hero:lang(ja) { --shimpz-type-display-size: clamp(1rem, 4.9vw, 3.3rem); }
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
  @media (prefers-reduced-motion: reduce) {
    .glitch-title::before,
    .glitch-title::after { animation: none; }
  }
  @media (forced-colors: active) {
    h1,
    .title-accent { color: CanvasText; }
  }
</style>
