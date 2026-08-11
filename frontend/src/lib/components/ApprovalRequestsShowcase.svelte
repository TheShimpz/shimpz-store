<script lang="ts">
  import { onMount } from "svelte";
  import { ActionLink } from "@shimpz/frontend";
  import type { HomepageHumanRequests } from "$lib/homepage";
  import {
    HOMEPAGE_REQUEST_ROTATION_MS,
    HOMEPAGE_REQUESTS,
  } from "$lib/homepageRequests";

  let { content }: { content: HomepageHumanRequests } = $props();
  let activeIndex = $state(0);
  let hovered = $state(false);
  let focusWithin = $state(false);
  let requestMenu: HTMLDivElement | undefined = $state();
  const activeRequest = $derived(HOMEPAGE_REQUESTS[activeIndex]);
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
      const left = Math.max(0, Math.min(
        button.offsetLeft - (requestMenu.clientWidth - button.offsetWidth) / 2,
        requestMenu.scrollWidth - requestMenu.clientWidth,
      ));
      requestMenu.scrollTo({
        left,
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
  data-slot="homepage-power-requests"
  data-active-kind={activeRequest.kind}
  data-rotation-ms={HOMEPAGE_REQUEST_ROTATION_MS}
  aria-labelledby="power-requests-title">
  <header class="intro">
    <div>
      <p class="kicker">SHIMPZ SDK // POWER HUMAN REQUESTS</p>
      <h2 id="power-requests-title">{content.heading}</h2>
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
    aria-labelledby="power-requests-title"
    onpointerenter={startHover}
    onpointerleave={stopHover}
    onfocusin={() => focusWithin = true}
    onfocusout={resumeAfterFocus}>
    <div class="request-menu" dir="ltr" bind:this={requestMenu}>
      <ol aria-label={content.menuLabel}>
        {#each HOMEPAGE_REQUESTS as request, index (request.kind)}
          <li>
            <button
              type="button"
              class:active={index === activeIndex}
              aria-current={index === activeIndex ? "true" : undefined}
              onclick={() => selectRequest(index)}>
              <span class="number">{String(index + 1).padStart(2, "0")}</span>
              <span class="request-name">
                <strong>{request.kind}</strong>
                <code>{request.call}</code>
              </span>
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
      <div class="slides">
        {#each HOMEPAGE_REQUESTS as request, index (request.kind)}
          <figure
            class:active={index === activeIndex}
            aria-hidden={index === activeIndex ? undefined : "true"}>
            <img
              src={`/power-requests/${request.image}`}
              alt={index === activeIndex ? `${content.imageAlt} ${request.kind}` : ""}
              width="512"
              height={request.height}
              loading="eager"
              fetchpriority={index === 0 ? "high" : "low"}
            />
          </figure>
        {/each}
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
  .request-menu button { position: relative; display: grid; width: 100%; grid-template-columns: 2rem minmax(0, 1fr); gap: .9rem; align-items: center; padding: .8rem .75rem; color: var(--color-muted); text-align: start; background: transparent; border: 0; cursor: pointer; }
  .request-menu button::before { position: absolute; inset-block: 0; inset-inline-start: 0; width: 2px; content: ""; background: transparent; }
  .request-menu button:hover, .request-menu button:focus-visible, .request-menu button.active { color: var(--color-text); background: var(--color-surface); }
  .request-menu button.active::before { background: var(--color-green); box-shadow: 0 0 12px color-mix(in srgb, var(--color-green) 65%, transparent); }
  .request-menu button:focus-visible { z-index: 1; outline: 2px solid var(--color-yellow); outline-offset: -2px; }
  .number { color: var(--color-green); font: 600 .66rem/1 var(--font-mono); letter-spacing: .1em; }
  .request-name { display: grid; min-width: 0; gap: .22rem; }
  .request-name strong { overflow: hidden; font: 650 .82rem/1.2 var(--font-mono); text-overflow: ellipsis; white-space: nowrap; }
  .request-name code { overflow: hidden; color: var(--color-muted); font: 400 .62rem/1.3 var(--font-mono); text-overflow: ellipsis; white-space: nowrap; }
  .request-stage { display: grid; min-width: 0; min-height: 44rem; align-content: start; gap: 1rem; }
  .stage-heading { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 1rem; color: var(--color-muted); font: 600 .66rem/1 var(--font-mono); letter-spacing: .12em; text-transform: uppercase; }
  .stage-heading code { overflow: hidden; color: var(--color-cyan); font: inherit; text-overflow: ellipsis; white-space: nowrap; }
  .signature { display: block; overflow-wrap: anywhere; color: var(--color-text); font: 500 .72rem/1.5 var(--font-mono); }
  .slides { position: relative; display: grid; place-items: start center; }
  figure { position: absolute; inset: 0; display: grid; width: 100%; justify-items: center; margin: 0; visibility: hidden; opacity: 0; pointer-events: none; transition: opacity 180ms ease; }
  figure.active { position: relative; visibility: visible; opacity: 1; pointer-events: auto; }
  img { display: block; width: min(100%, 32rem); height: auto; object-fit: contain; }
  .group-note { min-height: 4rem; max-inline-size: 40rem; margin: 0 auto; color: var(--color-muted); font-size: .88rem; line-height: 1.65; text-align: center; }
  @media (max-width: 760px) {
    section { gap: 2.5rem; padding-block: 4.5rem; }
    .intro { grid-template-columns: 1fr; gap: 2rem; }
    h2 { max-inline-size: 16ch; font-size: clamp(2.15rem, 11vw, 3.25rem); }
    .showcase { grid-template-columns: 1fr; gap: 2rem; }
    .request-menu { overflow-x: auto; overscroll-behavior-inline: contain; scrollbar-width: thin; }
    .request-menu ol { display: flex; width: max-content; }
    .request-menu li { width: min(15rem, 72vw); border-block-end: 0; border-inline-end: 1px solid var(--color-border); }
    .request-menu li:last-child { border-inline-end: 0; }
    .request-stage { min-height: 38rem; }
    .group-note { min-height: 6rem; }
    .stage-heading { align-items: start; flex-direction: column; }
  }
  @media (prefers-reduced-motion: reduce) {
    figure { transition: none; }
  }
</style>
