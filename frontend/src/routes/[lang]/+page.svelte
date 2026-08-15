<script lang="ts">
  import {
    ActionLink,
    Button,
    EditorialHero,
    EditorialSection,
    ShimpzBrand,
    TextAreaField,
  } from "@shimpz/frontend";
  import { goto } from "$app/navigation";
  import { onMount, tick } from "svelte";
  import type { Locale } from "$lib/catalog";
  import HomepageCatalog from "$lib/components/HomepageCatalog.svelte";
  import HomepageMeshBackground from "$lib/components/HomepageMeshBackground.svelte";
  import HudIcon, { type HudIconName } from "$lib/components/HudIcon.svelte";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import {
    homepage,
    HOMEPAGE_TASK_HOLD_MS,
    HOMEPAGE_TASK_TYPING_DELAY_MS,
  } from "$lib/homepage";
  import { tr } from "$lib/i18n";
  import { MAX_PENDING_TASK_CHARS, savePendingTask } from "$lib/pendingTask.js";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(homepage(lang));

  const userIcons: HudIconName[] = ["check", "team", "local"];
  const developerIcons: HudIconName[] = ["check", "session", "shield"];
  let firstTask = $state("");
  let taskError = $state("");
  let taskReady = $state(false);
  let taskField: HTMLTextAreaElement | undefined = $state();
  let animatedTaskPrompt = $state("");
  let taskPromptVisible = $state(false);
  let taskPromptPaused = $state(false);
  let reducedMotion = $state(false);
  let taskInteracted = false;
  let cancelTaskPromptAnimation = () => {};
  let setTaskPromptPaused = (_paused: boolean) => {};

  onMount(() => {
    taskReady = true;
    void tick().then(() => taskField?.focus({ preventScroll: true }));
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncMotionPreference = () => {
      reducedMotion = motionPreference.matches;
    };
    syncMotionPreference();
    motionPreference.addEventListener("change", syncMotionPreference);

    return () => motionPreference.removeEventListener("change", syncMotionPreference);
  });

  $effect(() => {
    const examples = content.taskExamples;
    const stablePrompt = content.taskPlaceholder;
    if (!taskReady || taskInteracted || reducedMotion) {
      taskPromptVisible = false;
      return;
    }

    const segmenter = new Intl.Segmenter(lang, { granularity: "grapheme" });
    const graphemes = (value: string) => Array.from(segmenter.segment(value), ({ segment }) => segment);
    const stable = graphemes(stablePrompt);
    type Frame = { text: string; example: string; phase: "stable" | "type" | "erase"; delay: number };
    const frames = [
      ...stable.map((_, index): Frame => ({
        text: stable.slice(0, stable.length - index - 1).join(""),
        example: examples[0],
        phase: "stable",
        delay: HOMEPAGE_TASK_TYPING_DELAY_MS,
      })),
      ...examples.flatMap((example): Frame[] => {
        const characters = graphemes(example);
        return [
          ...characters.map((_, index): Frame => ({
            text: characters.slice(0, index + 1).join(""),
            example,
            phase: "type",
            delay: index === characters.length - 1
              ? HOMEPAGE_TASK_HOLD_MS
              : HOMEPAGE_TASK_TYPING_DELAY_MS,
          })),
          ...characters.map((_, index): Frame => ({
            text: characters.slice(0, characters.length - index - 1).join(""),
            example,
            phase: "erase",
            delay: HOMEPAGE_TASK_TYPING_DELAY_MS,
          })),
        ];
      }),
    ] satisfies Frame[];
    let frameIndex = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;
    let paused = false;
    let activeExample = examples[0];

    animatedTaskPrompt = stablePrompt;
    taskPromptVisible = true;
    taskPromptPaused = false;

    // An indefinite loop keeps a keyboard-accessible pause control that reveals itself on focus.
    const advance = () => {
      if (cancelled || paused) return;
      const frame = frames[frameIndex];
      animatedTaskPrompt = frame.text;
      activeExample = frame.example;
      frameIndex = frameIndex + 1 >= frames.length ? stable.length : frameIndex + 1;
      timer = setTimeout(advance, frame.delay);
    };
    timer = setTimeout(advance, HOMEPAGE_TASK_TYPING_DELAY_MS);

    const setPaused = (nextPaused: boolean) => {
      if (cancelled || nextPaused === paused) return;
      paused = nextPaused;
      taskPromptPaused = nextPaused;
      if (timer !== undefined) clearTimeout(timer);
      if (nextPaused) {
        animatedTaskPrompt = activeExample;
        const firstEraseFrame = frames.findIndex(
          (frame) => frame.example === activeExample && frame.phase === "erase",
        );
        if (firstEraseFrame >= 0) frameIndex = firstEraseFrame;
        return;
      }
      timer = setTimeout(advance, HOMEPAGE_TASK_TYPING_DELAY_MS);
    };
    setTaskPromptPaused = setPaused;

    const cancel = () => {
      cancelled = true;
      if (timer !== undefined) clearTimeout(timer);
      taskPromptVisible = false;
    };
    cancelTaskPromptAnimation = cancel;

    return () => {
      cancel();
      if (cancelTaskPromptAnimation === cancel) cancelTaskPromptAnimation = () => {};
      if (setTaskPromptPaused === setPaused) setTaskPromptPaused = () => {};
    };
  });

  function startFirstTask(event: SubmitEvent) {
    event.preventDefault();
    taskError = "";
    try {
      if (!savePendingTask(sessionStorage, firstTask)) return;
    } catch {
      taskError = content.taskStorageError;
      return;
    }
    void goto(u.chat(lang));
  }

  function handleFirstTaskKeydown(event: KeyboardEvent) {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    if (firstTask.trim()) (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
  }

  function handleFirstTaskInput() {
    taskInteracted = true;
    cancelTaskPromptAnimation();
  }
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />

{#snippet heroMedia()}
  <div class="hero-brand" data-slot="homepage-brand-monument">
    <ShimpzBrand variant="symbol" decorative />
  </div>
{/snippet}

{#snippet heroActions()}
  <form class="hero-task" onsubmit={startFirstTask}>
    <div class="hero-task-prompt">
      <TextAreaField
        id="homepage-first-task"
        class="hero-task-field"
        label={content.taskLabel}
        visuallyHiddenLabel
        placeholder={content.taskPlaceholder}
        maxlength={MAX_PENDING_TASK_CHARS}
        autocomplete="off"
        disabled={!taskReady}
        rows={2}
        error={taskError || undefined}
        bind:element={taskField}
        bind:value={firstTask}
        oninput={handleFirstTaskInput}
        onkeydown={handleFirstTaskKeydown}
      />
      {#if taskPromptVisible}
        <span
          class="task-prompt-typing"
          data-slot="homepage-task-typing"
          aria-hidden="true"
          dir="auto"
        >{animatedTaskPrompt}</span>
      {/if}
    </div>
    <Button type="submit" disabled={!taskReady || !firstTask.trim()}>{content.taskSubmit} →</Button>
    {#if taskPromptVisible}
      <Button
        type="button"
        class="task-prompt-toggle"
        variant="ghost"
        size="compact"
        onclick={() => setTaskPromptPaused(!taskPromptPaused)}
      >
        {taskPromptPaused ? content.taskAnimationResume : content.taskAnimationPause}
      </Button>
    {/if}
  </form>
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
      <EditorialHero
        class="homepage-hero"
        kicker={content.intro}
        title={content.title}
        lead={content.lead}
        titleId="hero-title"
        media={heroMedia}
        actions={heroActions}
      />
    </div>

    <div class="surface-band evidence-band" data-slot="homepage-evidence-band">
      <div class="editorial-wrap evidence-section">
        <ul class="hero-differentials" data-slot="homepage-differentials" role="list">
          <li><a href={u.openSource(lang)}><span aria-hidden="true">01</span>{tr("nav_open_source", lang)}</a></li>
          <li><a href={u.security(lang)}><span aria-hidden="true">02</span>{tr("nav_security", lang)}</a></li>
        </ul>
        <div data-slot="homepage-install-command"><InstallCommand {lang} /></div>
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
  .hero-space {
    padding-block: clamp(2.75rem, 5vw, 4.5rem);
  }
  :global(section[data-slot="editorial-hero"].homepage-hero) {
    --shimpz-type-display-size: clamp(2.15rem, 3.4vw, 3.5rem);
    --shimpz-type-display-measure: 30ch;
    --homepage-hero-column-gap: clamp(var(--shimpz-space-8), 6vw, var(--shimpz-space-16));
    display: grid;
    grid-template-columns: minmax(29.5rem, 0.8fr) minmax(0, 1.2fr);
    column-gap: var(--homepage-hero-column-gap);
    row-gap: var(--shimpz-space-4);
    align-items: center;
  }
  :global(.homepage-hero > header) { grid-column: 2; grid-row: 1; align-self: end; }
  :global(.homepage-hero > header > .kicker) { text-transform: none; }
  :global(.homepage-hero > .body.has-media) { display: contents; }
  :global(.homepage-hero > .body.has-media > .copy) { grid-column: 2; grid-row: 2; align-self: start; }
  :global(.homepage-hero > .body.has-media > [data-slot="editorial-hero-media"]) {
    grid-column: 1;
    grid-row: 1 / span 2;
    width: 100%;
    min-width: 0;
    align-self: center;
  }
  .hero-task {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    width: 100%;
    gap: var(--shimpz-space-3);
    align-items: start;
  }
  .hero-task :global(.shimpz-button[type="submit"]) { width: 100%; }
  .hero-task-prompt { position: relative; min-width: 0; }
  .hero-task :global(.task-prompt-toggle) {
    --button-color: var(--color-fg);
    --button-hover-color: var(--color-cyan);
    position: absolute;
    inset-block-start: calc(100% + var(--shimpz-space-3));
    inset-inline-end: 0;
    inline-size: 1px;
    block-size: 1px;
    min-block-size: 0;
    overflow: hidden;
    padding: 0;
    border: 0;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  .hero-task :global(.task-prompt-toggle:focus-visible) {
    --button-bg: var(--shimpz-color-surface-raised);
    position: fixed;
    z-index: 10;
    inset-block-start: auto;
    inset-block-end: var(--shimpz-space-4);
    inset-inline-end: var(--shimpz-space-4);
    inline-size: auto;
    block-size: auto;
    min-block-size: var(--shimpz-control-height-compact);
    overflow: visible;
    padding: 0.45rem 0.65rem;
    border: 1px solid var(--button-border);
    clip-path: polygon(
      0 0,
      calc(100% - var(--shimpz-cut)) 0,
      100% var(--shimpz-cut),
      100% 100%,
      0 100%
    );
  }
  .task-prompt-typing {
    position: absolute;
    z-index: 1;
    inset-block-start: 0.65rem;
    inset-inline: 0.7rem;
    max-height: 3rem;
    overflow: hidden;
    color: var(--shimpz-color-text-muted);
    font: 400 1rem/1.5 var(--shimpz-font-sans);
    overflow-wrap: anywhere;
    pointer-events: none;
    text-align: start;
    white-space: pre-wrap;
  }
  .evidence-section { display: grid; gap: var(--shimpz-space-6); padding-block: clamp(2rem, 4vw, 3.5rem); }
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
  .hero-task :global(.shimpz-field textarea) { min-height: 0; }
  .hero-task :global(.shimpz-field textarea::placeholder) {
    color: var(--shimpz-color-text-muted);
    opacity: 1;
  }
  .hero-task-prompt:has(> [data-slot="homepage-task-typing"])
    :global(.shimpz-field textarea::placeholder) {
    color: transparent;
  }
  .surface-band { border-block: 1px solid var(--color-border); background: var(--color-surface); }
  .section-space { padding-block: clamp(2.5rem, 5vw, 4.5rem); }
  .hero-brand {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .hero-brand :global([data-slot="shimpz-brand-mark"]) {
    width: clamp(16rem, 33vw, 30rem);
    height: clamp(16rem, 33vw, 30rem);
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
    :global(section[data-slot="editorial-hero"].homepage-hero) {
      --shimpz-type-display-size: clamp(1.65rem, 6.9vw, 2rem);
      --shimpz-type-display-measure: 22ch;
      grid-template-columns: 1fr;
      row-gap: var(--shimpz-space-4);
    }
    :global(.homepage-hero > header) { grid-column: 1; grid-row: auto; }
    :global(.homepage-hero > .body.has-media) {
      display: grid;
      grid-column: 1;
      grid-row: auto;
      grid-template-columns: 1fr;
      gap: var(--shimpz-space-8);
      align-items: start;
    }
    :global(.homepage-hero > .body.has-media > .copy),
    :global(.homepage-hero > .body.has-media > [data-slot="editorial-hero-media"]) {
      grid-column: 1;
      grid-row: auto;
    }
    :global(.homepage-hero > .body.has-media > [data-slot="editorial-hero-media"]) {
      position: static;
      width: auto;
      transform: none;
    }
    .hero-brand { min-height: min(70vw, 16rem); }
    .hero-brand :global([data-slot="shimpz-brand-mark"]) {
      width: min(70vw, 16rem);
      height: min(70vw, 16rem);
    }
    .feature-list { grid-template-columns: 1fr; }
    .feature-list li { min-height: auto; border-inline-end: 0; border-block-end: 1px solid var(--color-border); }
    .feature-list li:last-child { border-block-end: 0; }
  }
</style>
