<script lang="ts">
  import {
    ActionLink,
    EditorialHero,
    EditorialSection,
    ShimpzBrand,
  } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import HudIcon, { type HudIconName } from "$lib/components/HudIcon.svelte";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { institutional } from "$lib/institutional";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutional(lang));

  const stepIcons: HudIconName[] = ["chat", "assistants", "shield"];
  const controlIcons: HudIconName[] = ["key", "user", "shield", "eye"];
  const profileIcons: HudIconName[] = ["local", "hosted"];
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet heroMedia()}
  <div class="hero-brand" data-slot="homepage-brand-monument">
    <ShimpzBrand variant="hero" decorative />
  </div>
{/snippet}

{#snippet heroMeta()}<InstallCommand {lang} />{/snippet}

{#snippet heroActions()}
  <ActionLink href={u.install(lang)} variant="primary">{content.installTitle}</ActionLink>
  <ActionLink href={u.assistants(lang)} variant="ghost">{content.assistantsLink}</ActionLink>
{/snippet}

{#snippet securityAction()}
  <ActionLink href={u.security(lang)}>{content.securityLink}</ActionLink>
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
            <div class="concept-mark"><span>0{index + 1}</span><HudIcon name={stepIcons[index]} size={26} /></div>
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
    actions={securityAction}
  >
    <ul class="control-list" data-slot="concept-list">
      {#each content.controls as control, index (control.title)}
        <li>
          <div class="concept-mark"><span>0{index + 1}</span><HudIcon name={controlIcons[index]} size={26} /></div>
          <div><h3>{control.title}</h3><p>{control.body}</p></div>
        </li>
      {/each}
    </ul>
  </EditorialSection>
</div>

<div class="surface-band">
  <div class="editorial-wrap">
    <EditorialSection
      kicker={content.profilesKicker}
      title={content.profilesTitle}
      lead={content.profilesLead}
      titleId="profiles-title"
    >
      <ul class="profiles-grid" data-slot="concept-list">
        {#each content.profiles as profile, index (profile.title)}
          <li>
            <div class="concept-mark"><span>0{index + 1}</span><HudIcon name={profileIcons[index]} size={28} /></div>
            <span class="profile-name">{profile.title}</span>
            <h3>{profile.body}</h3>
            <p>{profile.detail}</p>
          </li>
        {/each}
      </ul>
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
  .hero-brand { --shimpz-brand-hero-mark-size: clamp(8rem, 22vw, 15rem); --shimpz-brand-hero-word-size: clamp(3rem, 8vw, 7rem); display: flex; min-height: clamp(16rem, 31vw, 25rem); align-items: center; justify-content: center; }
  .steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .steps li { display: grid; min-height: 14rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .steps li:last-child { border-inline-end: 0; }
  .concept-mark { display: flex; align-items: center; justify-content: space-between; color: var(--color-cyan); }
  .concept-mark span, .profile-name { color: var(--color-cyan); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }
  .steps h3, .control-list h3, .profiles-grid h3 { margin: 0 0 .6rem; font-size: 1.05rem; line-height: 1.25; }
  .steps p, .control-list p, .profiles-grid p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  .control-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .control-list li { display: grid; min-height: 13rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); border-block-end: 1px solid var(--color-border); }
  .control-list li:nth-child(2n) { border-inline-end: 0; }
  .control-list li:nth-last-child(-n + 2) { border-block-end: 0; }
  .profiles-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .profiles-grid li { min-height: 15rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .profiles-grid li:last-child { border-inline-end: 0; }
  .profiles-grid .profile-name { display: block; margin-block-start: 2.5rem; }
  .profiles-grid h3 { margin-block-start: 3rem; }
  .open-source { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1fr); align-items: start; gap: clamp(2rem, 8vw, 8rem); padding-block: clamp(5rem, 10vw, 9rem); }
  .actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-block-start: 1.5rem; }
  @media (max-width: 760px) {
    .install-grid, .open-source { grid-template-columns: 1fr; }
    .hero-brand { min-height: 15rem; }
    .steps, .control-list, .profiles-grid { grid-template-columns: 1fr; }
    .steps li, .control-list li, .profiles-grid li { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .steps li:last-child, .control-list li:last-child, .profiles-grid li:last-child { border-block-end: 0; }
    .control-list li:nth-last-child(2) { border-block-end: 1px solid var(--color-border); }
    .profiles-grid h3 { margin-block-start: 2rem; }
  }
</style>
