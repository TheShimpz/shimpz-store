<script lang="ts">
  import { Card, ShimpzBrand } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import Seo from "$lib/components/Seo.svelte";
  import { institutional } from "$lib/institutional";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutional(lang));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

<section class="hero wrap" aria-labelledby="hero-title">
  <div class="hero-copy">
    <p class="kicker">{content.eyebrow}</p>
    <h1 id="hero-title">{content.title}</h1>
    <p class="lead">{content.lead}</p>
    <p class="support">{content.support}</p>
    <div class="actions">
      <a class="cta primary" href={u.assistants(lang)}>{content.explore}</a>
      <a class="cta secondary" href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer">{content.documentation} ↗</a>
    </div>
  </div>
  <div class="hero-mark" aria-hidden="true">
    <ShimpzBrand variant="symbol" />
    <span>Space</span>
    <i></i>
  </div>
</section>

<section class="section wrap" aria-labelledby="profiles-title">
  <header class="section-heading">
    <p class="kicker">{content.profilesKicker}</p>
    <h2 id="profiles-title">{content.profilesTitle}</h2>
    <p>{content.profilesLead}</p>
  </header>
  <div class="profile-grid">
    {#each content.profiles as profile (profile.title)}
      <Card class="institutional-card">
        <span class="card-index">{profile.title}</span>
        <h3>{profile.title} Space</h3>
        <p>{profile.body}</p>
        <small>{profile.detail}</small>
      </Card>
    {/each}
  </div>
</section>

<section class="section architecture" aria-labelledby="architecture-title">
  <div class="wrap">
    <header class="section-heading">
      <p class="kicker">{content.architectureKicker}</p>
      <h2 id="architecture-title">{content.architectureTitle}</h2>
      <p>{content.architectureLead}</p>
    </header>
    <div class="concept-grid">
      {#each content.concepts as concept, index (concept.title)}
        <article>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <h3>{concept.title}</h3>
          <p>{concept.body}</p>
        </article>
      {/each}
    </div>
  </div>
</section>

<section class="section wrap" aria-labelledby="publication-title">
  <header class="section-heading wide">
    <p class="kicker">{content.publicationKicker}</p>
    <h2 id="publication-title">{content.publicationTitle}</h2>
    <p>{content.publicationLead}</p>
  </header>
  <ol class="publication-flow">
    {#each content.flow as item, index (item.title)}
      <li>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <div><h3>{item.title}</h3><p>{item.body}</p></div>
      </li>
    {/each}
  </ol>
</section>

<section class="section open-source" aria-labelledby="open-title">
  <div class="wrap open-grid">
    <div>
      <p class="kicker">{content.openKicker}</p>
      <h2 id="open-title">{content.openTitle}</h2>
    </div>
    <div>
      <p>{content.openBody}</p>
      <div class="actions">
        <a class="cta primary" href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer">{content.github} ↗</a>
        <a class="cta ghost" href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer">{content.documentation} ↗</a>
      </div>
    </div>
  </div>
</section>

<section class="section final wrap" aria-labelledby="final-title">
  <p class="kicker">Shimpz // Space</p>
  <h2 id="final-title">{content.finalTitle}</h2>
  <p>{content.finalBody}</p>
  <div class="actions">
    <a class="cta primary" href={u.assistants(lang)}>{content.explore}</a>
    <a class="cta secondary" href={u.services(lang)}>Services</a>
    <a class="cta ghost" href={u.creators(lang)}>Creators</a>
  </div>
</section>

<style>
  .hero {
    display: grid;
    min-height: min(760px, calc(100dvh - 5.25rem));
    grid-template-columns: minmax(0, 1.2fr) minmax(18rem, 0.65fr);
    align-items: center;
    gap: clamp(3rem, 8vw, 8rem);
    padding-block: clamp(5rem, 10vw, 9rem);
  }
  .hero-copy { max-width: 58rem; }
  .kicker { margin: 0 0 1rem; color: var(--color-cyan); font: 600 0.68rem/1.4 var(--font-mono); letter-spacing: 0.15em; text-transform: uppercase; }
  h1 { max-width: 13ch; margin: 0; font-size: clamp(3rem, 7.8vw, 7.4rem); line-height: 0.9; letter-spacing: -0.065em; }
  .lead { max-width: 62ch; margin: 2rem 0 0; color: var(--color-fg); font-size: clamp(1.08rem, 1.8vw, 1.35rem); line-height: 1.6; }
  .support { max-width: 68ch; margin: 1rem 0 0; color: var(--color-muted); line-height: 1.7; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-block-start: 2rem; }
  .cta { display: inline-flex; min-height: var(--shimpz-control-height); align-items: center; justify-content: center; padding: .6rem .9rem; color: var(--shimpz-color-text-muted); font: 700 .72rem/1 var(--shimpz-font-mono); letter-spacing: .07em; border: 1px solid var(--shimpz-color-border); clip-path: polygon(0 0,calc(100% - var(--shimpz-cut)) 0,100% var(--shimpz-cut),100% 100%,0 100%); text-transform: uppercase; }
  .cta.primary { color: var(--shimpz-color-bg); background: var(--shimpz-color-cyan); border-color: var(--shimpz-color-cyan); }
  .cta.secondary { color: var(--shimpz-color-cyan); background: var(--shimpz-color-surface-raised); border-color: var(--shimpz-color-cyan); }
  .cta:hover { color: var(--shimpz-color-bg); background: var(--shimpz-color-text); border-color: var(--shimpz-color-text); box-shadow: var(--shimpz-glow-cyan); }
  .hero-mark { position: relative; display: grid; aspect-ratio: 1; place-items: center; background: radial-gradient(circle, rgba(0,240,255,.13), transparent 65%); border: 1px solid var(--color-border); clip-path: polygon(12% 0,100% 0,100% 88%,88% 100%,0 100%,0 12%); }
  .hero-mark :global(.shimpz-brand) { transform: scale(2.2); }
  .hero-mark span { position: absolute; inset-block-end: 1.2rem; inset-inline-start: 1.4rem; font: 600 0.68rem/1 var(--font-mono); letter-spacing: .16em; text-transform: uppercase; }
  .hero-mark i { position: absolute; inset-block-start: 1rem; inset-inline-end: 1rem; width: .55rem; height: .55rem; background: var(--color-green); border-radius: 50%; box-shadow: 0 0 12px var(--color-green); }
  .section { padding-block: clamp(5rem, 10vw, 9rem); }
  .section-heading { max-width: 64rem; margin-block-end: clamp(2.5rem, 6vw, 4rem); }
  .section-heading.wide { max-width: 72rem; }
  h2 { max-width: 18ch; margin: 0; font-size: clamp(2.2rem, 5vw, 4.7rem); line-height: .98; letter-spacing: -.05em; }
  .section-heading > p:last-child, .open-grid p, .final > p { max-width: 68ch; color: var(--color-muted); font-size: 1rem; line-height: 1.75; }
  .profile-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  :global(.institutional-card) { min-height: 20rem; padding: clamp(1.5rem, 4vw, 2.5rem); }
  :global(.institutional-card h3) { margin: auto 0 1rem; font-size: clamp(1.7rem, 4vw, 2.8rem); }
  :global(.institutional-card p) { color: var(--color-muted); line-height: 1.7; }
  :global(.institutional-card small), .card-index { color: var(--color-muted-2); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .08em; text-transform: uppercase; }
  .architecture, .open-source { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .concept-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-block-start: 1px solid var(--color-border); border-inline-start: 1px solid var(--color-border); }
  .concept-grid article { min-height: 18rem; padding: 1.5rem; border-block-end: 1px solid var(--color-border); border-inline-end: 1px solid var(--color-border); }
  .concept-grid span, .publication-flow > li > span { color: var(--color-cyan); font: 600 .65rem/1 var(--font-mono); }
  .concept-grid h3, .publication-flow h3 { margin: 3rem 0 1rem; font-size: 1.15rem; }
  .concept-grid p, .publication-flow p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  .publication-flow { display: grid; padding: 0; grid-template-columns: repeat(3, minmax(0, 1fr)); list-style: none; border: 1px solid var(--color-border); }
  .publication-flow li { display: grid; min-height: 16rem; grid-template-rows: auto 1fr; padding: 1.5rem; border-inline-end: 1px solid var(--color-border); }
  .publication-flow li:last-child { border-inline-end: 0; }
  .publication-flow div { align-self: end; }
  .publication-flow h3 { margin-block-start: 0; }
  .open-grid { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1fr); gap: clamp(2rem, 8vw, 8rem); }
  .final { text-align: center; }
  .final h2, .final > p { margin-inline: auto; }
  .final .actions { justify-content: center; }
  @media (max-width: 980px) { .concept-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 760px) {
    .hero, .open-grid { grid-template-columns: 1fr; }
    .hero { min-height: auto; }
    .hero-mark { width: min(100%, 24rem); }
    .profile-grid, .publication-flow { grid-template-columns: 1fr; }
    .publication-flow li { min-height: 12rem; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .publication-flow li:last-child { border-block-end: 0; }
  }
  @media (max-width: 480px) { .concept-grid { grid-template-columns: 1fr; } .concept-grid article { min-height: 14rem; } }
</style>
