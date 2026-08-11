<script lang="ts">
  import { onMount } from "svelte";
  import { ActionLink, Button, DialogFrame } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import AssistantHumanRequestBody from "$lib/components/AssistantHumanRequestBody.svelte";
  import { localeDirection } from "$lib/locales";
  import type { HomepageHumanRequests } from "$lib/homepage";
  import {
    HOMEPAGE_REQUEST_ROTATION_MS,
    HOMEPAGE_REQUESTS,
    homepageRequestChallenge,
    homepageRequestLabel,
  } from "$lib/homepageRequests";
  import {
    humanRequestKicker,
    humanRequestPrimaryLabel,
  } from "$lib/humanRequestPresentation";
  import { tr } from "$lib/i18n";

  let { content, lang }: { content: HomepageHumanRequests; lang: Locale } = $props();
  let activeIndex = $state(0);
  let hovered = $state(false);
  let focusWithin = $state(false);
  let fieldValue = $state<any>();
  let fieldValid = $state(false);
  let requestMenu: HTMLDivElement | undefined = $state();
  const activeRequest = $derived(HOMEPAGE_REQUESTS[activeIndex]);
  const activeChallenge = $derived(homepageRequestChallenge(activeRequest, lang));
  const paused = $derived(hovered || focusWithin);

  function startHover(event: PointerEvent): void {
    if (event.pointerType === "mouse") hovered = true;
  }

  function stopHover(): void {
    hovered = false;
  }

  function selectRequest(index: number): void {
    activeIndex = index;
    window.requestAnimationFrame(() => {
      if (!requestMenu || requestMenu.scrollWidth <= requestMenu.clientWidth) return;
      const button = requestMenu.querySelectorAll<HTMLButtonElement>("button")[index];
      if (!button) return;
      button.scrollIntoView({
        block: "nearest",
        inline: "center",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      });
    });
  }

  function resumeAfterFocus(event: FocusEvent): void {
    const container = event.currentTarget;
    const next = event.relatedTarget;
    if (container instanceof HTMLElement && !(next instanceof Node && container.contains(next))) focusWithin = false;
  }

  onMount(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => {
      if (!paused && document.visibilityState === "visible") {
        selectRequest((activeIndex + 1) % HOMEPAGE_REQUESTS.length);
      }
    }, HOMEPAGE_REQUEST_ROTATION_MS);
    return () => window.clearInterval(timer);
  });
</script>

<section
  id="demo"
  data-slot="homepage-action-requests"
  data-active-kind={activeRequest.kind}
  data-rotation-ms={HOMEPAGE_REQUEST_ROTATION_MS}
  aria-labelledby="action-requests-title">
  <header class="intro">
    <div>
      <p class="kicker">SHIMPZ SDK // ACTION HUMAN REQUESTS</p>
      <h2 id="action-requests-title">{content.heading}</h2>
      <p class="lead">{content.body}</p>
    </div>
    <div class="sdk-copy">
      <p>{content.sdkSummary}</p>
      <ActionLink href="https://github.com/TheShimpz/shimpz-sdk" variant="ghost">
        {content.sdkCta} →
      </ActionLink>
    </div>
  </header>

  <div
    class="showcase"
    role="group"
    aria-labelledby="action-requests-title"
    onpointerenter={startHover}
    onpointerleave={stopHover}
    onfocusin={() => focusWithin = true}
    onfocusout={resumeAfterFocus}>
    <div class="request-menu" dir={localeDirection(lang)} bind:this={requestMenu}>
      <ol aria-label={content.menuLabel}>
        {#each HOMEPAGE_REQUESTS as request, index (request.kind)}
          <li>
            <button
              type="button"
              data-request-kind={request.kind}
              class:active={index === activeIndex}
              aria-current={index === activeIndex ? "true" : undefined}
              aria-label={homepageRequestLabel(request, lang)}
              title={homepageRequestLabel(request, lang)}
              onclick={() => selectRequest(index)}>
              <span class="number">{String(index + 1).padStart(2, "0")}</span>
              <strong>{homepageRequestLabel(request, lang)}</strong>
            </button>
          </li>
        {/each}
      </ol>
    </div>

    <div class="request-stage">
      <div class="stage-heading">
        <span>{content.interfaceLabel}</span>
        <code>{activeRequest.kind}</code>
      </div>
      <code class="signature">{activeRequest.signature}</code>
      <div class="request-preview" data-slot="homepage-request-preview">
        <form autocomplete="off" onsubmit={(event) => event.preventDefault()}>
          <DialogFrame
            kicker={humanRequestKicker(activeRequest.kind, lang)}
            title={activeChallenge.request.title}
            titleId="homepage-request-preview-title"
            titleLevel={3}
          >
            <AssistantHumanRequestBody
              challenge={activeChallenge}
              {lang}
              presentation
              bind:fieldValue
              bind:fieldValid
            />
            {#snippet footer()}
              <Button type="button" variant="secondary" disabled>{tr("human_cancel", lang)}</Button>
              <Button type="button" disabled>{humanRequestPrimaryLabel(activeRequest.kind, lang)}</Button>
            {/snippet}
          </DialogFrame>
        </form>
      </div>
      <p class="group-note">{content.groupNotes[activeRequest.group]}</p>
    </div>
  </div>
</section>

<style>
  section { display: grid; gap: clamp(2.5rem, 5vw, 4.5rem); padding-block: clamp(5rem, 9vw, 8rem); scroll-margin-block-start: 7rem; }
  .intro { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(18rem, .8fr); gap: clamp(2rem, 6vw, 6rem); align-items: end; }
  .kicker { margin: 0 0 1rem; color: var(--color-cyan); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .16em; text-transform: uppercase; }
  h2 { max-inline-size: 14ch; margin: 0; color: var(--color-text); font-size: clamp(2.4rem, 5vw, 4.8rem); font-weight: 680; letter-spacing: -.045em; line-height: .98; text-wrap: balance; }
  .lead { max-inline-size: 42rem; margin: 1.5rem 0 0; color: var(--color-muted); font-size: clamp(1rem, 1.5vw, 1.2rem); line-height: 1.65; }
  .sdk-copy { display: grid; justify-items: start; gap: 1.5rem; }
  .sdk-copy p { max-inline-size: 34rem; margin: 0; color: var(--color-text); font-size: 1rem; line-height: 1.65; }
  .showcase { display: grid; grid-template-columns: minmax(16rem, .72fr) minmax(0, 1.28fr); gap: clamp(2rem, 5vw, 5rem); align-items: start; }
  .request-menu { min-width: 0; border-block: 1px solid var(--color-border); }
  .request-menu ol { margin: 0; padding: 0; list-style: none; }
  .request-menu li { border-block-end: 1px solid var(--color-border); }
  .request-menu li:last-child { border-block-end: 0; }
  .request-menu button { position: relative; display: grid; width: 100%; grid-template-columns: 2rem minmax(0, 1fr); gap: .9rem; align-items: center; padding: .72rem .75rem; color: var(--color-muted); text-align: start; background: transparent; border: 0; cursor: pointer; }
  .request-menu button::before { position: absolute; inset-block: 0; inset-inline-start: 0; width: 2px; content: ""; background: transparent; }
  .request-menu button:hover, .request-menu button:focus-visible, .request-menu button.active { color: var(--color-text); background: var(--color-surface); }
  .request-menu button.active::before { background: var(--color-green); box-shadow: 0 0 12px color-mix(in srgb, var(--color-green) 65%, transparent); }
  .request-menu button:focus-visible { z-index: 1; outline: 2px solid var(--color-yellow); outline-offset: -2px; }
  .number { color: var(--color-green); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; }
  .request-menu button strong { font: 650 clamp(.66rem, .8vw, .8rem)/1.2 var(--font-mono); white-space: nowrap; }
  .request-stage { display: grid; min-width: 0; min-height: 42rem; align-content: start; gap: 1rem; }
  .stage-heading { display: flex; min-width: 0; min-height: 1.5rem; align-items: center; justify-content: space-between; gap: 1rem; color: var(--color-muted); font: 600 .66rem/1 var(--font-mono); letter-spacing: .12em; text-transform: uppercase; }
  .stage-heading code { overflow: hidden; color: var(--color-cyan); font: inherit; text-overflow: ellipsis; white-space: nowrap; }
  .signature { display: block; block-size: 2.25rem; overflow: auto; overflow-wrap: anywhere; color: var(--color-text); font: 500 .72rem/1.5 var(--font-mono); }
  .request-preview { display: grid; min-width: 0; place-items: start center; }
  .request-preview form { container-type: inline-size; width: min(100%, 27.6rem); margin-inline: auto; }
  .request-preview :global(.shimpz-dialog-frame) { max-height: none; }
  .request-preview :global(.shimpz-dialog-frame footer) { flex-wrap: wrap; }
  .group-note { min-block-size: 5rem; max-inline-size: 40rem; margin: 0 auto; color: var(--color-muted); font-size: .88rem; line-height: 1.65; text-align: center; }
  @media (max-width: 1080px) {
    section { gap: 2.5rem; padding-block: 4.5rem; }
    .intro { grid-template-columns: 1fr; gap: 2rem; }
    h2 { max-inline-size: 16ch; font-size: clamp(2.15rem, 11vw, 3.25rem); }
    .showcase { grid-template-columns: 1fr; gap: 2rem; }
    .request-menu { overflow-x: auto; overscroll-behavior-inline: contain; scrollbar-width: thin; }
    .request-menu ol { display: flex; width: max-content; }
    .request-menu li { width: max-content; min-width: min(17rem, 76vw); border-block-end: 0; border-inline-end: 1px solid var(--color-border); }
    .request-menu li:last-child { border-inline-end: 0; }
    .request-menu button { width: max-content; min-width: 100%; }
    .request-stage { min-height: 46rem; }
    .group-note { min-block-size: 7rem; }
    .stage-heading { align-items: start; flex-direction: column; }
  }
</style>
