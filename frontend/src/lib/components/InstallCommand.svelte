<script lang="ts">
  import { Button } from "@shimpz/frontend";
  import { onDestroy } from "svelte";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";

  const command = "curl -fsSL https://install.shimpz.com | sh";
  let { lang }: { lang: Locale } = $props();
  let copyState = $state<"idle" | "copied" | "error">("idle");
  let resetTimer: ReturnType<typeof setTimeout> | undefined;
  let copyButton = $state<HTMLButtonElement>();

  function fallbackCopy(): boolean {
    const textarea = document.createElement("textarea");
    textarea.value = command;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.inset = "-9999px auto auto -9999px";
    document.body.appendChild(textarea);
    textarea.select();

    const copied = document.execCommand("copy");
    textarea.remove();
    copyButton?.focus();
    return copied;
  }

  async function copyCommand() {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(command);
      } else if (!fallbackCopy()) {
        throw new Error("Clipboard unavailable");
      }
      copyState = "copied";
      if (resetTimer) clearTimeout(resetTimer);
      resetTimer = setTimeout(() => (copyState = "idle"), 1800);
    } catch {
      copyState = "error";
      if (resetTimer) clearTimeout(resetTimer);
      resetTimer = setTimeout(() => (copyState = "idle"), 2400);
    }
  }

  onDestroy(() => {
    if (resetTimer) clearTimeout(resetTimer);
  });
</script>

{#snippet copyIcon()}
  {#if copyState === "copied"}
    <svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
  {:else}
    <svg viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="11" /><path d="M16 8V5H5v11h3" /></svg>
  {/if}
{/snippet}

<div class="install-command">
  <div class="command-shell">
    <span class="prompt" aria-hidden="true">$</span>
    <code>{command}</code>
    <Button
      bind:element={copyButton}
      class={['copy-button', copyState === "error" && "error"]}
      variant="secondary"
      size="lg"
      icon={copyIcon}
      glitch
      type="button"
      onclick={copyCommand}
      aria-label={tr(copyState === "copied" ? "home_copied" : copyState === "error" ? "home_copy_failed" : "home_copy", lang)}
    >
      {tr(copyState === "copied" ? "home_copied" : copyState === "error" ? "home_copy_failed" : "home_copy", lang)}
    </Button>
    <span class="sr-status" aria-live="polite">
      {copyState === "copied" ? tr("home_copied", lang) : copyState === "error" ? tr("home_copy_failed", lang) : ""}
    </span>
  </div>
  <a class="script-link" href="https://install.shimpz.com" target="_blank" rel="noopener noreferrer">
    {tr("home_read_script", lang)} <span aria-hidden="true">↗</span>
  </a>
</div>

<style>
  .install-command {
    display: grid;
    gap: var(--shimpz-space-3);
  }

  .command-shell {
    display: grid;
    min-height: 4.25rem;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.8rem;
    padding: 0.75rem 0.8rem 0.75rem 1.1rem;
    background: transparent;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(var(--cut) 0, 100% 0, 100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%, 0 100%, 0 var(--cut));
  }

  .prompt,
  code,
  :global(.copy-button) {
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

  :global(.copy-button) {
    min-width: 6.4rem;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
  }

  :global(.copy-button:hover) { box-shadow: inset 0 0 0 1px var(--color-cyan); }
  :global(.copy-button.error) { color: var(--color-danger); box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-danger) 70%, var(--color-border)); }

  .script-link {
    justify-self: center;
    color: var(--color-muted);
    font: 600 0.68rem/1.2 var(--font-mono);
    letter-spacing: 0.08em;
    text-decoration: none;
    text-transform: uppercase;
  }

  .script-link:hover,
  .script-link:focus-visible { color: var(--color-cyan); }

  :global([dir="rtl"]) .script-link { letter-spacing: normal; }

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

    :global(.copy-button) { grid-column: 1 / -1; width: 100%; }
  }
</style>
