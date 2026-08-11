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

  const developerIcons: HudIconName[] = ["check", "session", "shield"];
  const userIcons: HudIconName[] = ["check", "team", "local"];
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet heroMedia()}
  <div class="hero-brand" data-slot="homepage-brand-monument">
    <ShimpzBrand variant="hero" decorative />
  </div>
{/snippet}

{#snippet heroActions()}
  <ActionLink href="https://docs.shimpz.com/developers/assistants/spec/" variant="primary">
    {content.readSpec} →
  </ActionLink>
  <ActionLink href={u.assistants(lang)} variant="ghost">{content.browseAssistants} →</ActionLink>
{/snippet}

{#snippet developersAction()}
  <ActionLink href="https://docs.shimpz.com/developers/assistants/quickstart/" variant="primary">
    {content.developersCta} →
  </ActionLink>
{/snippet}

{#snippet usersAction()}
  <ActionLink href={u.assistants(lang)} variant="primary">{content.browseAssistants} →</ActionLink>
{/snippet}

<div class="editorial-wrap hero-space">
  <EditorialHero
    title={content.title}
    lead={content.lead}
    titleId="hero-title"
    media={heroMedia}
    actions={heroActions}
  />
</div>

<div class="surface-band">
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

<div class="editorial-wrap">
  <HomepageCatalog {content} />
</div>

<div class="surface-band">
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
</div>

<style>
  .editorial-wrap { width: min(100% - 2rem, var(--shimpz-editorial-width)); margin-inline: auto; }
  .hero-space { padding-block: clamp(4rem, 8vw, 7rem); }
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
  .feature-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0; border: 1px solid var(--color-border); list-style: none; }
  .feature-list li { display: grid; min-height: 15rem; align-content: space-between; gap: 2rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  .feature-list li:last-child { border-inline-end: 0; }
  .feature-mark { display: flex; align-items: center; justify-content: space-between; color: var(--color-cyan); }
  .feature-mark span { color: var(--color-cyan); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; }
  .feature-list h3 { margin: 0 0 .6rem; font-size: 1.05rem; line-height: 1.25; }
  .feature-list p { margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  @media (max-width: 760px) {
    .hero-brand { min-height: 15rem; }
    .feature-list { grid-template-columns: 1fr; }
    .feature-list li { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .feature-list li:last-child { border-block-end: 0; }
  }
</style>
