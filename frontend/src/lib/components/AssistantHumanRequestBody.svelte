<script lang="ts">
  import { Notice, ActionRequestFields } from "@shimpz/frontend";
  import type { Locale } from "$lib/locales";
  import { humanRequestContextParts } from "$lib/humanRequestContext";
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
  const context = $derived(humanRequestContextParts(tr("human_context", lang), challenge));
</script>

<p class="context">{#each context as part}{#if part.emphasized}<strong><bdi>{part.text}</bdi></strong>{:else}{part.text}{/if}{/each}</p>

{#if presentation}
  <fieldset class="presentation-fields" disabled aria-label={tr("human_preview", lang)}>
    <ActionRequestFields
      {request}
      resetKey={challenge.challenge_id}
      labels={fieldLabels}
      bind:value={fieldValue}
      bind:valid={fieldValid}
    />
  </fieldset>
{:else}
  <ActionRequestFields
    {request}
    resetKey={challenge.challenge_id}
    labels={fieldLabels}
    bind:value={fieldValue}
    bind:valid={fieldValid}
  />
{/if}

{#if validationError}<Notice variant="error">{validationError}</Notice>{/if}

<style>
  .context { margin: 0; color: var(--shimpz-color-text-dim); font-size: 0.78rem; line-height: 1.55; }
  .context strong { color: var(--shimpz-color-cyan); font-family: var(--shimpz-font-mono); font-weight: 700; }
  .presentation-fields { display: contents; margin: 0; border: 0; padding: 0; }
</style>
