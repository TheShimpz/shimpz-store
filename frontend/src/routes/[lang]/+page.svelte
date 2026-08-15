<script lang="ts">
  import {
    ActionLink,
    EditorialSection,
    ShimpzBrand,
  } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import HomepageCatalog from "$lib/components/HomepageCatalog.svelte";
  import HomepageMeshBackground from "$lib/components/HomepageMeshBackground.svelte";
  import HomepageVideo from "$lib/components/HomepageVideo.svelte";
  import HudIcon, { type HudIconName } from "$lib/components/HudIcon.svelte";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { homepage } from "$lib/homepage";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(homepage(lang));

  const userIcons: HudIconName[] = ["check", "team", "local"];
  const developerIcons: HudIconName[] = ["check", "session", "shield"];
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet brandSymbol(slot = "homepage-brand-monument")}
  <div class="hero-brand" data-slot={slot}>
    <ShimpzBrand variant="symbol" decorative />
  </div>
{/snippet}

{#snippet usersAction()}
  <ActionLink href={u.assistants(lang)} variant="primary">{content.meetAssistants} →</ActionLink>
{/snippet}

{#snippet developersAction()}
  <ActionLink href="https://docs.shimpz.com/developers/assistants/spec/" variant="primary">
    {content.developersCta} →
  </ActionLink>
{/snippet}

<div class="homepage-shell">
  <HomepageMeshBackground />
  <div class="homepage-content" data-slot="homepage-content">
    <div class="editorial-wrap hero-space">
      <section data-slot="editorial-hero" class="homepage-hero">
        <header>
          <p class="kicker">{content.intro}</p>
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

    <div class="surface-band evidence-band" data-slot="homepage-evidence-band">
      <div class="editorial-wrap evidence-section">
        <ul class="hero-differentials" data-slot="homepage-differentials" role="list">
          <li><a href={u.openSource(lang)}><span aria-hidden="true">01</span>{tr("nav_open_source", lang)}</a></li>
          <li><a href={u.security(lang)}><span aria-hidden="true">02</span>{tr("nav_security", lang)}</a></li>
        </ul>
        <div class="evidence-install-row">
          {@render brandSymbol("homepage-install-brand")}
          <div data-slot="homepage-install-command"><InstallCommand {lang} /></div>
        </div>
      </div>
    </div>

    <div class="editorial-wrap section-space">
      <EditorialSection
        title={content.usersHeading}
        lead={content.usersBody}
        titleId="users-title"
        actions={usersAction}
      >
        <ol class="feature-list user-features" data-slot="homepage-user-features">
          {#each content.userFeatures as feature, index (feature.title)}
            <li>
              <div class="feature-mark">
                <span>0{index + 1}</span>
                <HudIcon name={userIcons[index]} size={26} />
              </div>
              <div><h3>{feature.title}</h3><p>{feature.body}</p></div>
            </li>
          {/each}
        </ol>
      </EditorialSection>
    </div>

    <div class="surface-band">
      <div class="editorial-wrap">
        <HomepageCatalog {content} catalogHref={u.assistants(lang)} />
      </div>
    </div>

    <div class="editorial-wrap section-space">
      <EditorialSection
        title={content.developersHeading}
        lead={content.developersBody}
        titleId="developers-title"
        actions={developersAction}
      >
        <ol class="feature-list developer-features" data-slot="homepage-developer-features">
          {#each content.developerFeatures as feature, index (feature.title)}
            <li>
              <div class="feature-mark">
                <span>0{index + 1}</span>
                <HudIcon name={developerIcons[index]} size={26} />
              </div>
              <div><h3>{feature.title}</h3><p>{feature.body}</p></div>
            </li>
          {/each}
        </ol>
      </EditorialSection>
    </div>
  </div>
</div>

<style>
  .homepage-shell { position: relative; isolation: isolate; }
  .homepage-content { position: relative; z-index: 1; }
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space,
  .section-space { padding-block: clamp(2.5rem, 5vw, 4.5rem); }
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
  .kicker {
    margin: 0 0 var(--shimpz-space-4);
    color: var(--color-cyan);
    font: 600 0.68rem/1.4 var(--font-mono);
    letter-spacing: 0.16em;
    text-transform: none;
  }
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
  .evidence-section { display: grid; gap: var(--shimpz-space-6); padding-block: clamp(2rem, 4vw, 3.5rem); }
  .evidence-install-row { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: clamp(2rem, 5vw, 4rem); }
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
  .surface-band { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .hero-brand {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .hero-brand :global([data-slot="shimpz-brand-mark"]) {
    width: clamp(7.5rem, 12vw, 10rem);
    height: clamp(7.5rem, 12vw, 10rem);
  }
  .evidence-band { background: var(--color-bg); }
  .feature-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .feature-list li { display: grid; min-height: 15rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .feature-list li:last-child { border-inline-end: 0; }
  .feature-mark { display: flex; align-items: center; justify-content: space-between; color: var(--color-cyan); }
  .feature-mark span { color: var(--color-cyan); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; }
  .feature-list h3 { margin: 0 0 .6rem; font-size: 1.05rem; line-height: 1.25; }
  .feature-list p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  @media (max-width: 900px) {
    .homepage-hero {
      --shimpz-type-display-size: clamp(1.65rem, 6.9vw, 2rem);
      --shimpz-type-display-measure: 22ch;
    }
    .feature-list { grid-template-columns: 1fr; }
    .feature-list li { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .feature-list li:last-child { border-block-end: 0; }
  }
  @media (max-width: 620px) {
    .evidence-install-row { grid-template-columns: 1fr; }
    .hero-brand { justify-content: start; }
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
