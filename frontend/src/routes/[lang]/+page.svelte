<script lang="ts">
  import { ActionLink, Card, ShimpzBrand } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
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
    <div class="hero-install"><InstallCommand {lang} /></div>
    <div class="actions">
      <ActionLink href={u.install(lang)} variant="primary">{content.installTitle}</ActionLink>
      <ActionLink href={u.assistants(lang)} variant="ghost">{content.assistantsLink}</ActionLink>
    </div>
  </div>

  <div class="control-map" aria-hidden="true">
    <div class="brand-node"><ShimpzBrand variant="symbol" /><span>Shimpz</span></div>
    <div class="map-line"></div>
    <div class="team-node">Team</div>
    <div class="assistant-nodes"><span>Assistant 01</span><span>Assistant 02</span><span>Assistant 03</span></div>
    <div class="approval-node"><i></i> Human approval</div>
  </div>
</section>

<section class="section install-section" aria-labelledby="install-title">
  <div class="wrap split">
    <div>
      <p class="kicker">{content.installKicker}</p>
      <h2 id="install-title">{content.installTitle}</h2>
    </div>
    <p class="section-lead">{content.installBody}</p>
  </div>
</section>

<section class="section wrap" aria-labelledby="problem-title">
  <header class="section-heading">
    <p class="kicker">{content.problemKicker}</p>
    <h2 id="problem-title">{content.problemTitle}</h2>
    <p>{content.problemLead}</p>
  </header>
  <div class="two-grid">
    {#each content.alternatives as item, index (item.title)}
      <Card class="story-card" tone={index === 1 ? "accent" : "default"}>
        <span class="card-index">0{index + 1}</span>
        <h3>{item.title}</h3>
        <p>{item.body}</p>
      </Card>
    {/each}
  </div>
</section>

<section class="section model" aria-labelledby="model-title">
  <div class="wrap">
    <header class="section-heading">
      <p class="kicker">{content.modelKicker}</p>
      <h2 id="model-title">{content.modelTitle}</h2>
      <p>{content.modelLead}</p>
    </header>
    <ol class="step-grid">
      {#each content.steps as step, index (step.title)}
        <li><span>0{index + 1}</span><div><h3>{step.title}</h3><p>{step.body}</p></div></li>
      {/each}
    </ol>
  </div>
</section>

<section class="section wrap" aria-labelledby="control-title">
  <header class="section-heading wide">
    <p class="kicker">{content.controlKicker}</p>
    <h2 id="control-title">{content.controlTitle}</h2>
    <p>{content.controlLead}</p>
  </header>
  <div class="control-grid">
    {#each content.controls as control (control.title)}
      <article><i></i><h3>{control.title}</h3><p>{control.body}</p></article>
    {/each}
  </div>
  <div class="inline-action"><ActionLink href={u.security(lang)}>{content.securityLink}</ActionLink></div>
</section>

<section class="section profiles" aria-labelledby="profiles-title">
  <div class="wrap">
    <header class="section-heading">
      <p class="kicker">{content.profilesKicker}</p>
      <h2 id="profiles-title">{content.profilesTitle}</h2>
      <p>{content.profilesLead}</p>
    </header>
    <div class="two-grid">
      {#each content.profiles as profile (profile.title)}
        <Card class="profile-card">
          <span class="profile-label">{profile.title}</span>
          <h3>{profile.body}</h3>
          <p>{profile.detail}</p>
        </Card>
      {/each}
    </div>
  </div>
</section>

<section class="section wrap open-grid" aria-labelledby="open-title">
  <div>
    <p class="kicker">{content.openKicker}</p>
    <h2 id="open-title">{content.openTitle}</h2>
  </div>
  <div>
    <p class="section-lead">{content.openBody}</p>
    <div class="actions">
      <ActionLink href={u.openSource(lang)} variant="primary">{content.openLink}</ActionLink>
      <ActionLink href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer" variant="ghost">{content.github} ↗</ActionLink>
    </div>
  </div>
</section>

<section class="section final" aria-labelledby="final-title">
  <div class="wrap">
    <p class="kicker">{content.finalKicker}</p>
    <h2 id="final-title">{content.finalTitle}</h2>
    <p>{content.finalBody}</p>
    <div class="actions centered">
      <ActionLink href={u.install(lang)} variant="primary">{content.installTitle}</ActionLink>
      <ActionLink href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer" variant="ghost">{content.documentation} ↗</ActionLink>
    </div>
  </div>
</section>

<style>
  .hero { display: grid; min-height: min(780px, calc(100dvh - 5rem)); grid-template-columns: minmax(0, 1.15fr) minmax(20rem, .75fr); align-items: center; gap: clamp(3rem, 8vw, 8rem); padding-block: clamp(4rem, 9vw, 8rem); }
  .hero-copy { max-width: 62rem; }
  .kicker { margin: 0 0 1rem; color: var(--color-cyan); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .15em; text-transform: uppercase; }
  h1 { max-width: 14ch; margin: 0; font-size: clamp(3rem, 7vw, 6.8rem); line-height: .92; letter-spacing: -.065em; }
  .lead { max-width: 60ch; margin: 2rem 0 0; color: var(--color-fg); font-size: clamp(1.05rem, 1.8vw, 1.35rem); line-height: 1.6; }
  .support, .section-heading > p:last-child, .section-lead, .final p { max-width: 68ch; color: var(--color-muted); line-height: 1.75; }
  .support { margin-block-start: 1rem; }
  .hero-install { max-width: 50rem; margin-block-start: 2rem; }
  .actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-block-start: 1rem; }
  .control-map { position: relative; display: grid; min-height: 31rem; align-content: center; gap: 1rem; padding: clamp(1.5rem, 4vw, 2.5rem); overflow: hidden; background: radial-gradient(circle at 50% 30%, rgba(0,240,255,.14), transparent 55%), var(--color-surface); border: 1px solid var(--color-border); clip-path: polygon(12% 0,100% 0,100% 88%,88% 100%,0 100%,0 12%); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }
  .brand-node, .team-node, .assistant-nodes span, .approval-node { border: 1px solid var(--color-border-strong); background: #050505; }
  .brand-node { display: flex; align-items: center; gap: .8rem; justify-self: center; padding: 1rem 1.2rem; color: var(--color-cyan); }
  .brand-node :global(.shimpz-brand) { transform: scale(.85); }
  .map-line { width: 1px; height: 2rem; justify-self: center; background: var(--color-cyan); }
  .team-node { justify-self: center; padding: .9rem 2.5rem; }
  .assistant-nodes { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; }
  .assistant-nodes span { padding: .8rem .5rem; color: var(--color-muted); text-align: center; }
  .approval-node { display: flex; align-items: center; gap: .6rem; justify-self: center; padding: .8rem 1rem; color: var(--color-green); }
  .approval-node i, .control-grid i { width: .5rem; height: .5rem; background: var(--color-green); border-radius: 50%; box-shadow: 0 0 10px var(--color-green); }
  .section { padding-block: clamp(5rem, 10vw, 9rem); }
  .install-section, .model, .profiles, .final { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .split, .open-grid { display: grid; grid-template-columns: minmax(0,.8fr) minmax(0,1fr); gap: clamp(2rem,8vw,8rem); align-items: end; }
  .section-heading { max-width: 66rem; margin-block-end: clamp(2.5rem,6vw,4rem); }
  .section-heading.wide { max-width: 78rem; }
  h2 { max-width: 19ch; margin: 0; font-size: clamp(2.2rem,5vw,4.8rem); line-height: .98; letter-spacing: -.05em; }
  .two-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 1rem; }
  :global(.story-card), :global(.profile-card) { min-height: 18rem; }
  :global(.story-card .content), :global(.profile-card .content) { display: flex; height: 100%; flex-direction: column; }
  :global(.story-card h3), :global(.profile-card h3) { margin: auto 0 1rem; font-size: clamp(1.4rem,3vw,2.4rem); line-height: 1.1; }
  :global(.story-card p), :global(.profile-card p) { margin: 0; color: var(--color-muted); line-height: 1.7; }
  .card-index, .profile-label { color: var(--color-cyan); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }
  .step-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .step-grid li { display: grid; min-height: 17rem; align-content: space-between; padding: 1.5rem; border-inline-end: 1px solid var(--color-border); }
  .step-grid li:last-child { border-inline-end: 0; }
  .step-grid > li > span { color: var(--color-cyan); font: 600 .65rem/1 var(--font-mono); }
  .step-grid h3, .control-grid h3 { margin: 0 0 .8rem; font-size: 1.15rem; }
  .step-grid p, .control-grid p { margin: 0; color: var(--color-muted); font-size: .92rem; line-height: 1.65; }
  .control-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); border-block-start: 1px solid var(--color-border); border-inline-start: 1px solid var(--color-border); }
  .control-grid article { min-height: 15rem; padding: 1.5rem; border-block-end: 1px solid var(--color-border); border-inline-end: 1px solid var(--color-border); }
  .control-grid i { display: block; margin-block-end: 3rem; }
  .inline-action { margin-block-start: 1rem; }
  .open-grid { align-items: start; }
  .final { text-align: center; }
  .final h2, .final p { margin-inline: auto; }
  .centered { justify-content: center; }
  @media (max-width: 900px) { .control-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
  @media (max-width: 760px) { .hero, .split, .open-grid { grid-template-columns: 1fr; } .hero { min-height: auto; } .control-map { width: min(100%,30rem); min-height: 26rem; } .two-grid, .step-grid { grid-template-columns: 1fr; } .step-grid li { min-height: 12rem; border-inline-end: 0; border-block-end: 1px solid var(--color-border); } .step-grid li:last-child { border-block-end: 0; } }
  @media (max-width: 520px) { .control-grid, .assistant-nodes { grid-template-columns: 1fr; } .control-grid article { min-height: 12rem; } .assistant-nodes span:nth-child(n+3) { display: none; } }
  @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
</style>
