<script lang="ts">
  import { onDestroy } from "svelte";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";

  const command = "curl -fsSL https://install.shimpz.com | sh";
  let { lang }: { lang: Locale } = $props();
  let copied = $state(false);
  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
      copied = true;
      if (resetTimer) clearTimeout(resetTimer);
      resetTimer = setTimeout(() => (copied = false), 1800);
    } catch {
      copied = false;
    }
  }

  onDestroy(() => {
    if (resetTimer) clearTimeout(resetTimer);
  });
</script>

<div class="command-shell">
  <span class="prompt" aria-hidden="true">$</span>
  <code>{command}</code>
  <button type="button" onclick={copyCommand} aria-label={tr(copied ? "home_copied" : "home_copy", lang)}>
    {#if copied}
      <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
    {:else}
      <svg aria-hidden="true" viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="11" /><path d="M16 8V5H5v11h3" /></svg>
    {/if}
    <span>{tr(copied ? "home_copied" : "home_copy", lang)}</span>
  </button>
  <span class="sr-status" aria-live="polite">{copied ? tr("home_copied", lang) : ""}</span>
</div>

<style>
  .command-shell {
    display: grid;
    min-height: 4.25rem;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.8rem;
    padding: 0.75rem 0.8rem 0.75rem 1.1rem;
    background: #000000;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(9px 0, 100% 0, 100% calc(100% - 9px), calc(100% - 9px) 100%, 0 100%, 0 9px);
  }

  .prompt,
  code,
  button {
    font-family: var(--font-mono);
  }

  .prompt { color: var(--color-green); font-weight: 700; }

  code {
    min-width: 0;
    overflow-x: auto;
    color: var(--color-fg);
    font-size: clamp(0.7rem, 1.5vw, 0.84rem);
    scrollbar-width: thin;
    white-space: nowrap;
  }

  button {
    display: inline-flex;
    min-width: 6.4rem;
    min-height: 2.65rem;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    padding: 0.65rem 0.8rem;
    border: 0;
    background: var(--color-elevated);
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    color: var(--color-cyan);
    cursor: pointer;
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  button:hover { box-shadow: inset 0 0 0 1px var(--color-cyan); }

  svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: square;
    stroke-linejoin: miter;
    stroke-width: 1.8;
  }

  .sr-status {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 520px) {
    .command-shell {
      grid-template-columns: auto minmax(0, 1fr);
      padding: 1rem;
    }

    button { grid-column: 1 / -1; width: 100%; }
  }
</style>
