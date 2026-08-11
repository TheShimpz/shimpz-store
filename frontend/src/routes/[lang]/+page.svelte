<script lang="ts">
  import {
    ActionLink,
    EditorialHero,
    EditorialSection,
    ShimpzBrand,
  } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import HomepageCatalog from "$lib/components/HomepageCatalog.svelte";
  import HudIcon, { type HudIconName } from "$lib/components/HudIcon.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { homepage } from "$lib/homepage";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(homepage(lang));

  const userIcons: HudIconName[] = ["check", "team", "local"];
  const developerIcons: HudIconName[] = ["check", "session", "shield"];
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet heroMedia()}
  <div class="hero-brand" data-slot="homepage-brand-monument">
    <ShimpzBrand variant="hero" decorative />
  </div>
{/snippet}

{#snippet heroActions()}
  <ActionLink href={u.assistants(lang)} variant="primary">{content.meetAssistants} →</ActionLink>
  <ActionLink href="#demo" variant="ghost">{content.watchMeWork} →</ActionLink>
{/snippet}

{#snippet usersAction()}
  <ActionLink href={u.assistants(lang)} variant="primary">{content.meetAssistants} →</ActionLink>
{/snippet}

{#snippet developersAction()}
  <ActionLink href="https://docs.shimpz.com/developers/assistants/spec/" variant="primary">
    {content.developersCta} →
  </ActionLink>
{/snippet}

<div class="editorial-wrap hero-space">
  <EditorialHero
    class="homepage-hero"
    title={content.title}
    lead={content.lead}
    titleId="hero-title"
    media={heroMedia}
    actions={heroActions}
  />
</div>

<div class="surface-band demo-band">
  <div class="editorial-wrap demo-space">
    <figure id="demo" data-slot="homepage-demo" data-demo-state="todo" aria-labelledby="demo-caption">
      <div class="demo-pending">
        <span class="todo-label">TODO</span>
        <HudIcon name="chat" size={48} />
        <strong>{content.demoPending}</strong>
      </div>
      <figcaption id="demo-caption">{content.demoCaption}</figcaption>
    </figure>
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

<style>
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space { padding-block: clamp(4rem, 8vw, 7rem); }
  :global(.homepage-hero) {
    --shimpz-type-display-size: clamp(2.15rem, 4.2vw, 4rem);
    --shimpz-type-display-measure: 40ch;
  }
  .surface-band { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .section-space { padding-block: clamp(5rem, 10vw, 9rem); }
  .hero-brand {
    --shimpz-brand-hero-mark-size: clamp(8rem, 22vw, 15rem);
    --shimpz-brand-hero-word-size: clamp(3rem, 8vw, 7rem);
    display: flex;
    min-height: clamp(16rem, 31vw, 25rem);
    align-items: center;
    justify-content: center;
  }
  .demo-band { background: var(--color-bg); }
  .demo-space { padding-block: clamp(4rem, 8vw, 7rem); }
  figure { display: grid; gap: 1.5rem; margin: 0; }
  .demo-pending {
    display: grid;
    min-height: clamp(17rem, 34vw, 28rem);
    place-content: center;
    justify-items: center;
    gap: 1.25rem;
    color: var(--color-cyan);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
  }
  .demo-pending strong { color: var(--color-muted); font: 600 .72rem/1.5 var(--font-mono); letter-spacing: .08em; text-align: center; text-transform: uppercase; }
  .todo-label { padding: .45rem .65rem; color: var(--color-bg); font: 800 .7rem/1 var(--font-mono); letter-spacing: .12em; background: var(--color-yellow); }
  figcaption { color: var(--color-text); font-size: clamp(1.25rem, 2.5vw, 2rem); font-weight: 650; line-height: 1.3; text-wrap: balance; }
  .feature-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .feature-list li { display: grid; min-height: 15rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .feature-list li:last-child { border-inline-end: 0; }
  .feature-mark { display: flex; align-items: center; justify-content: space-between; color: var(--color-cyan); }
  .feature-mark span { color: var(--color-cyan); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; }
  .feature-list h3 { margin: 0 0 .6rem; font-size: 1.05rem; line-height: 1.25; }
  .feature-list p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  @media (max-width: 760px) {
    :global(.homepage-hero) { --shimpz-type-display-size: clamp(1.65rem, 6.9vw, 2rem); }
    .hero-brand { min-height: 15rem; }
    .demo-pending { min-height: 15rem; }
    .feature-list { grid-template-columns: 1fr; }
    .feature-list li { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .feature-list li:last-child { border-block-end: 0; }
  }
</style>
