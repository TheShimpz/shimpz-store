<script lang="ts">
  import { Card, Notice, PowerRequestFields } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { humanRequestFieldLabels } from "$lib/humanRequestPresentation";
  import { tr } from "$lib/i18n";

  let {
    challenge,
    lang,
    presentation = false,
    validationError = "",
    fieldValue = $bindable(),
    fieldValid = $bindable(false),
  }: {
    challenge: any;
    lang: Locale;
    presentation?: boolean;
    validationError?: string;
    fieldValue?: any;
    fieldValid?: boolean;
  } = $props();

  const request = $derived(challenge?.request ?? {});
  const fieldLabels = $derived(humanRequestFieldLabels(request, lang));
</script>

<p class="paused">
  {tr("human_paused", lang)}
  <span>{tr("human_expires", lang)} {challenge.expires_in} {tr("human_seconds", lang)}.</span>
</p>
<Card class="request-origin" padding="compact">
  <div><span>{tr("human_assistant", lang)}</span><strong>{challenge.assistant.name}</strong><code>{challenge.assistant.id}</code></div>
  <div><span>{tr("human_power", lang)}</span><strong>{challenge.power.summary}</strong><code>{challenge.power.id}</code></div>
</Card>

{#if presentation}
  <fieldset class="presentation-fields" disabled aria-label={tr("human_preview", lang)}>
    <PowerRequestFields
      {request}
      resetKey={challenge.challenge_id}
      labels={fieldLabels}
      bind:value={fieldValue}
      bind:valid={fieldValid}
    />
  </fieldset>
{:else}
  <PowerRequestFields
    {request}
    resetKey={challenge.challenge_id}
    labels={fieldLabels}
    bind:value={fieldValue}
    bind:valid={fieldValid}
  />
{/if}

{#if validationError}<Notice variant="error">{validationError}</Notice>{/if}

<style>
  .paused { margin: 0; color: var(--shimpz-color-text-dim); font-size: 0.72rem; line-height: 1.5; }
  .paused span { color: var(--shimpz-color-cyan); font-family: var(--shimpz-font-mono); }
  .presentation-fields { display: contents; margin: 0; border: 0; padding: 0; }
  :global(.request-origin > [data-slot="card-content"]) { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--shimpz-space-4); }
  :global(.request-origin [data-slot="card-content"] > div) { display: grid; min-width: 0; gap: 0.18rem; }
  :global(.request-origin span) { color: var(--shimpz-color-text-faint); font: 600 0.58rem/1.2 var(--shimpz-font-mono); letter-spacing: 0.08em; text-transform: uppercase; }
  :global(.request-origin strong) { overflow: hidden; font-size: 0.78rem; line-height: 1.4; text-overflow: ellipsis; }
  :global(.request-origin code) { overflow: hidden; color: var(--shimpz-color-cyan); font-size: 0.6rem; text-overflow: ellipsis; }
  @media (max-width: 520px) { :global(.request-origin > [data-slot="card-content"]) { grid-template-columns: 1fr; } }
</style>
