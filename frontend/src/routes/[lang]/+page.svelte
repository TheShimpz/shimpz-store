<script lang="ts">
  import {
    ActionLink,
    EditorialHero,
    EditorialSection,
    EditorialVisual,
  } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { institutional } from "$lib/institutional";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutional(lang));

  const delegationSrcset = "/brand/illustrations/delegation-flow-v2-768.webp 768w, /brand/illustrations/delegation-flow-v2-1536.webp 1536w";
  const authorizationSrcset = "/brand/illustrations/authorization-flow-v2-768.webp 768w, /brand/illustrations/authorization-flow-v2-1536.webp 1536w";
  const profilesSrcset = "/brand/illustrations/space-profiles-v2-768.webp 768w, /brand/illustrations/space-profiles-v2-1536.webp 1536w";
  const delegationStages = $derived([
    content.steps[0].title,
    content.steps[1].title,
    content.steps[2].title,
    content.controls[3].title,
  ]);
  const authorizationStages = $derived([
    content.controls[0].title,
    content.controls[1].title,
    content.controls[3].title,
  ]);
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

<svelte:head>
  <link
    rel="preload"
    as="image"
    href="/brand/illustrations/delegation-flow-v2-1536.webp"
    imagesrcset={delegationSrcset}
    imagesizes="(max-width: 760px) calc(100vw - 2rem), 58vw"
  />
</svelte:head>

{#snippet heroMedia()}
  <div class="illustrated-diagram" data-diagram="delegation">
    <EditorialVisual
      src="/brand/illustrations/delegation-flow-v2-1536.webp"
      srcset={delegationSrcset}
      sizes="(max-width: 760px) calc(100vw - 2rem), 58vw"
      alt=""
      width={1536}
      height={1024}
      aspect="flow"
      fit="cover"
      treatment="unframed"
      priority
    />
    <ol class="diagram-legend legend-four" data-slot="diagram-legend" dir="ltr">
      {#each delegationStages as stage, index (index)}
        <li><span aria-hidden="true">0{index + 1}</span><strong dir="auto">{stage}</strong></li>
      {/each}
    </ol>
  </div>
{/snippet}

{#snippet heroMeta()}<InstallCommand {lang} />{/snippet}

{#snippet heroActions()}
  <ActionLink href={u.install(lang)} variant="primary">{content.installTitle}</ActionLink>
  <ActionLink href={u.assistants(lang)} variant="ghost">{content.assistantsLink}</ActionLink>
{/snippet}

{#snippet authorizationMedia()}
  <div class="illustrated-diagram" data-diagram="authorization">
    <EditorialVisual
      src="/brand/illustrations/authorization-flow-v2-1536.webp"
      srcset={authorizationSrcset}
      sizes="(max-width: 760px) calc(100vw - 2rem), 48vw"
      alt=""
      width={1536}
      height={1024}
      aspect="flow"
      fit="cover"
      treatment="unframed"
    />
    <ol class="diagram-legend legend-three" data-slot="diagram-legend" dir="ltr">
      {#each authorizationStages as stage, index (index)}
        <li><span aria-hidden="true">0{index + 1}</span><strong dir="auto">{stage}</strong></li>
      {/each}
    </ol>
  </div>
{/snippet}

{#snippet securityAction()}
  <ActionLink href={u.security(lang)}>{content.securityLink}</ActionLink>
{/snippet}

{#snippet profilesMedia()}
  <div class="illustrated-diagram" data-diagram="profiles">
    <EditorialVisual
      src="/brand/illustrations/space-profiles-v2-1536.webp"
      srcset={profilesSrcset}
      sizes="(max-width: 760px) calc(100vw - 2rem), 48vw"
      alt=""
      width={1536}
      height={1024}
      fit="contain"
      treatment="unframed"
    />
    <ul class="diagram-legend legend-two" data-slot="diagram-legend" dir="ltr">
      {#each content.profiles as profile (profile.title)}
        <li><strong>{profile.title}</strong><small dir="auto">{profile.detail}</small></li>
      {/each}
    </ul>
  </div>
{/snippet}

<div class="editorial-wrap hero-space">
  <EditorialHero
    kicker={content.eyebrow}
    title={content.title}
    lead={content.lead}
    titleId="hero-title"
    media={heroMedia}
    meta={heroMeta}
    actions={heroActions}
  />
</div>

<section class="install-band" aria-labelledby="install-title">
  <div class="editorial-wrap install-grid">
    <div>
      <p class="kicker">{content.installKicker}</p>
      <h2 id="install-title">{content.installTitle}</h2>
    </div>
    <p>{content.installBody}</p>
  </div>
</section>

<section class="editorial-wrap problem" aria-labelledby="problem-title">
  <p class="kicker">{content.problemKicker}</p>
  <h2 id="problem-title">{content.problemTitle}</h2>
  <p>{content.problemLead}</p>
</section>

<div class="surface-band">
  <div class="editorial-wrap">
    <EditorialSection
      kicker={content.modelKicker}
      title={content.modelTitle}
      lead={content.modelLead}
      titleId="model-title"
    >
      <ol class="steps">
        {#each content.steps as step, index (step.title)}
          <li>
            <span>0{index + 1}</span>
            <div><h3>{step.title}</h3><p>{step.body}</p></div>
          </li>
        {/each}
      </ol>
    </EditorialSection>
  </div>
</div>

<div class="editorial-wrap section-space">
  <EditorialSection
    kicker={content.controlKicker}
    title={content.controlTitle}
    lead={content.controlLead}
    titleId="control-title"
    media={authorizationMedia}
    actions={securityAction}
    mediaPosition="start"
  >
    <div class="control-list">
      {#each content.controls as control (control.title)}
        <article><i></i><div><h3>{control.title}</h3><p>{control.body}</p></div></article>
      {/each}
    </div>
  </EditorialSection>
</div>

<div class="surface-band">
  <div class="editorial-wrap">
    <EditorialSection
      kicker={content.profilesKicker}
      title={content.profilesTitle}
      lead={content.profilesLead}
      titleId="profiles-title"
      media={profilesMedia}
    >
      <div class="profiles-grid">
        {#each content.profiles as profile (profile.title)}
          <article>
            <span>{profile.title}</span>
            <h3>{profile.body}</h3>
            <p>{profile.detail}</p>
          </article>
        {/each}
      </div>
    </EditorialSection>
  </div>
</div>

<section class="editorial-wrap open-source" aria-labelledby="open-title">
  <div>
    <p class="kicker">{content.openKicker}</p>
    <h2 id="open-title">{content.openTitle}</h2>
  </div>
  <div>
    <p>{content.openBody}</p>
    <div class="actions">
      <ActionLink href={u.openSource(lang)} variant="primary">{content.openLink}</ActionLink>
      <ActionLink href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer" variant="ghost">{content.github} ↗</ActionLink>
    </div>
  </div>
</section>

<style>
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space { padding-block: clamp(4rem, 8vw, 7rem); }
  .kicker { margin: 0 0 1rem; color: var(--color-cyan); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .15em; text-transform: uppercase; }
  .install-band, .surface-band { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .install-grid { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1fr); align-items: end; gap: clamp(2rem, 8vw, 8rem); padding-block: clamp(3rem, 6vw, 5rem); }
  .install-grid h2 { max-width: var(--shimpz-type-section-measure); margin: 0; font: 650 var(--shimpz-type-section-size)/var(--shimpz-type-section-leading) var(--shimpz-font-sans); letter-spacing: var(--shimpz-type-section-tracking); text-wrap: balance; }
  .install-grid > p, .problem > p:last-child, .open-source > div > p { max-width: 68ch; margin: 0; color: var(--color-muted); line-height: 1.75; }
  .problem { padding-block: clamp(5rem, 9vw, 8rem); }
  .problem h2, .open-source h2 { max-width: var(--shimpz-type-section-measure); margin: 0 0 1.5rem; font: 680 var(--shimpz-type-section-size)/var(--shimpz-type-section-leading) var(--shimpz-font-sans); letter-spacing: var(--shimpz-type-section-tracking); text-wrap: balance; }
  .problem > p:last-child { font-size: clamp(1rem, 1.6vw, 1.25rem); }
  .surface-band > .editorial-wrap, .section-space { padding-block: clamp(5rem, 10vw, 9rem); }
  .illustrated-diagram { display: grid; gap: clamp(.75rem, 1.5vw, 1.25rem); width: 100%; }
  .diagram-legend { display: grid; gap: clamp(.65rem, 1.2vw, 1rem); min-width: 0; margin: 0; padding: 0; list-style: none; }
  .legend-four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .legend-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .legend-two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .diagram-legend li { display: grid; align-content: start; gap: .35rem; min-width: 0; color: var(--color-text); }
  .diagram-legend li > span { color: var(--color-green); font: 600 .62rem/1 var(--font-mono); letter-spacing: .1em; }
  .diagram-legend strong { font: 650 clamp(.72rem, 1vw, .86rem)/1.4 var(--font-sans); letter-spacing: -.01em; overflow-wrap: anywhere; }
  .diagram-legend small { display: block; color: var(--color-muted); font: 500 .68rem/1.5 var(--font-sans); text-align: start; overflow-wrap: anywhere; }
  .steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .steps li { display: grid; min-height: 14rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .steps li:last-child { border-inline-end: 0; }
  .steps span, .profiles-grid span { color: var(--color-cyan); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }
  .steps h3, .control-list h3, .profiles-grid h3 { margin: 0 0 .6rem; font-size: 1.05rem; line-height: 1.25; }
  .steps p, .control-list p, .profiles-grid p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  .control-list { display: grid; border-block-start: 1px solid var(--color-border); }
  .control-list article { display: grid; grid-template-columns: auto 1fr; gap: 1rem; padding-block: 1.15rem; border-block-end: 1px solid var(--color-border); }
  .control-list i { width: .5rem; height: .5rem; margin-block-start: .45rem; background: var(--color-green); border-radius: 50%; box-shadow: 0 0 10px var(--color-green); }
  .profiles-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border: 1px solid var(--color-border); }
  .profiles-grid article { min-height: 13rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .profiles-grid article:last-child { border-inline-end: 0; }
  .profiles-grid h3 { margin-block-start: 3rem; }
  .open-source { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1fr); align-items: start; gap: clamp(2rem, 8vw, 8rem); padding-block: clamp(5rem, 10vw, 9rem); }
  .actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-block-start: 1.5rem; }
  @media (max-width: 760px) {
    .install-grid, .open-source { grid-template-columns: 1fr; }
    .steps, .profiles-grid { grid-template-columns: 1fr; }
    .steps li, .profiles-grid article { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .steps li:last-child, .profiles-grid article:last-child { border-block-end: 0; }
    .profiles-grid h3 { margin-block-start: 2rem; }
    .diagram-legend { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .legend-three li:last-child { grid-column: 1 / -1; }
  }
</style>
