<script lang="ts">
  import { ActionLink, PageIntro } from "@shimpz/frontend";
  import { tr } from "$lib/i18n";
  import type { Locale } from "$lib/locales";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const title = $derived(tr("not_found_title", lang));
</script>

<svelte:head>
  <title>{title} — Shimpz</title>
  <meta name="robots" content="noindex,nofollow" />
</svelte:head>

{#snippet actions()}
  <ActionLink data-slot="not-found-home" href={u.home(lang)} variant="primary" size="lg">
    {tr("not_found_home", lang)}
  </ActionLink>
  <ActionLink data-slot="not-found-assistants" href={u.assistants(lang)} variant="ghost" size="lg">
    {tr("not_found_assistants", lang)}
  </ActionLink>
{/snippet}

<section class="not-found wrap" aria-labelledby="not-found-title">
  <div class="signal" data-slot="not-found-signal" aria-hidden="true" dir="ltr">
    <span class="signal-label">HTTP / ERROR</span>
    <strong data-text="404">404</strong>
    <div class="signal-state">
      <span></span>
      ROUTE_UNRESOLVED
    </div>
  </div>

  <PageIntro
    titleId="not-found-title"
    kicker={tr("not_found_kicker", lang)}
    {title}
    lead={tr("not_found_lead", lang)}
    {actions} />
</section>

<style>
  .not-found {
    display: grid;
    min-height: clamp(32rem, 66vh, 46rem);
    grid-template-columns: minmax(15rem, 0.82fr) minmax(0, 1.18fr);
    align-items: center;
    gap: clamp(2rem, 7vw, 7rem);
    padding-block: clamp(3rem, 8vw, 7rem);
  }

  .signal {
    position: relative;
    isolation: isolate;
    display: grid;
    width: min(100%, 28rem);
    aspect-ratio: 1;
    place-items: center;
    justify-self: end;
    overflow: hidden;
    color: var(--color-fg);
    background:
      linear-gradient(135deg, color-mix(in oklab, var(--color-cyan) 8%, transparent), transparent 42%),
      linear-gradient(315deg, color-mix(in oklab, var(--color-magenta) 7%, transparent), transparent 36%),
      var(--color-card);
    box-shadow:
      inset 0 0 0 1px var(--color-border-strong),
      inset 0 -5rem 8rem -7rem color-mix(in oklab, var(--color-cyan) 48%, transparent);
    clip-path: polygon(1.35rem 0, 100% 0, 100% calc(100% - 1.35rem), calc(100% - 1.35rem) 100%, 0 100%, 0 1.35rem);
  }

  .signal::before {
    content: "";
    position: absolute;
    z-index: -1;
    inset: 0;
    opacity: 0.36;
    background:
      linear-gradient(90deg, transparent 49.7%, var(--color-border-strong) 50%, transparent 50.3%),
      linear-gradient(0deg, transparent 49.7%, var(--color-border-strong) 50%, transparent 50.3%),
      repeating-radial-gradient(circle at center, transparent 0 2.85rem, var(--color-border) 2.9rem 3rem);
  }

  .signal::after {
    content: "";
    position: absolute;
    inset-block-start: 0;
    inset-inline-start: 1.35rem;
    width: 34%;
    height: 2px;
    background: var(--color-cyan);
    box-shadow: 0 0 1rem color-mix(in oklab, var(--color-cyan) 75%, transparent);
  }

  .signal-label,
  .signal-state {
    position: absolute;
    z-index: 2;
    font: 600 0.62rem/1.2 var(--font-mono);
    letter-spacing: 0.13em;
  }

  .signal-label {
    inset-block-start: 1.4rem;
    inset-inline-start: 1.5rem;
    color: var(--color-muted);
  }

  .signal strong {
    position: relative;
    z-index: 1;
    color: transparent;
    font: 700 clamp(5.8rem, 12vw, 10.5rem)/1 var(--font-mono);
    letter-spacing: -0.1em;
    -webkit-text-stroke: 1px var(--color-cyan);
    filter: drop-shadow(0 0 1.2rem color-mix(in oklab, var(--color-cyan) 20%, transparent));
  }

  .signal strong::after {
    content: attr(data-text);
    position: absolute;
    inset: 0;
    color: transparent;
    transform: translate(0.16rem, 0.16rem);
    -webkit-text-stroke: 1px color-mix(in oklab, var(--color-magenta) 72%, transparent);
  }

  .signal-state {
    inset-block-end: 1.4rem;
    inset-inline-end: 1.5rem;
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--color-muted);
  }

  .signal-state span {
    width: 0.42rem;
    aspect-ratio: 1;
    background: var(--color-magenta);
    box-shadow: 0 0 0.7rem color-mix(in oklab, var(--color-magenta) 70%, transparent);
  }

  :global(.not-found .shimpz-page-intro) {
    align-items: flex-start;
    flex-direction: column;
    border: 0;
    padding: 0;
  }

  :global(.not-found .shimpz-page-intro h1) {
    max-width: 14ch;
    font-family: var(--font-sans);
    font-size: clamp(2.2rem, 5vw, 4.8rem);
    font-weight: 680;
    line-height: 0.98;
    letter-spacing: -0.055em;
  }

  :global(.not-found .shimpz-page-intro .lead) {
    max-width: 46rem;
    margin-block-start: 1.1rem;
    font-size: clamp(1rem, 1.5vw, 1.12rem);
    line-height: 1.65;
  }

  :global(.not-found .shimpz-page-intro .actions) {
    gap: 0.75rem;
    margin-block-start: 1.25rem;
  }

  @media (max-width: 760px) {
    .not-found {
      min-height: auto;
      grid-template-columns: 1fr;
      gap: 2.5rem;
      padding-block: 3rem 4rem;
    }

    .signal {
      width: min(100%, 21rem);
      justify-self: center;
    }

    :global(.not-found .shimpz-page-intro) { align-items: stretch; }
    :global(.not-found .shimpz-page-intro .copy) { text-align: center; }
    :global(.not-found .shimpz-page-intro h1) { max-width: none; }
    :global(.not-found .shimpz-page-intro .actions) { justify-content: center; }
  }

  @media (max-width: 420px) {
    :global(.not-found .shimpz-page-intro .actions) {
      display: grid;
      width: 100%;
    }
  }

  @media (forced-colors: active) {
    .signal { border: 1px solid CanvasText; clip-path: none; }
    .signal::before,
    .signal::after,
    .signal-state span { display: none; }
    .signal strong,
    .signal strong::after { color: CanvasText; -webkit-text-stroke: 0; }
  }
</style>
