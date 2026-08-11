<script lang="ts">
  import { Notice, ActionRequestFields } from "@shimpz/frontend";
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
  const context = $derived(
    tr("human_context", lang)
      .replace("{action}", challenge.action.id)
      .replace("{assistant}", challenge.assistant.name)
      .replace("{version}", challenge.assistant.version)
      .replace("{seconds}", String(challenge.expires_in)),
  );
</script>

<p class="context">{context}</p>

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
  .presentation-fields { display: contents; margin: 0; border: 0; padding: 0; }
</style>
