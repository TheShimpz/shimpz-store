<script lang="ts">
  import { Button, PromptDialog } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import AssistantHumanRequestBody from "$lib/components/AssistantHumanRequestBody.svelte";
  import {
    humanRequestKicker,
    humanRequestPrimaryLabel,
  } from "$lib/humanRequestPresentation";
  import { tr } from "$lib/i18n";

  let {
    open = $bindable(false),
    challenge,
    lang,
    working = false,
    onrespond = (_response: any) => {},
  }: {
    open?: boolean;
    challenge: any;
    lang: Locale;
    working?: boolean;
    onrespond?: (response: any) => void;
  } = $props();

  let challengeId = $state("");
  let fieldValue = $state<any>();
  let fieldValid = $state(false);
  let validationError = $state("");

  const request = $derived(challenge?.request);
  const kind = $derived(request?.kind ?? "");
  const kicker = $derived(humanRequestKicker(kind, lang));
  const primaryLabel = $derived(humanRequestPrimaryLabel(kind, lang));

  $effect(() => {
    const nextId = challenge?.challenge_id ?? "";
    if (nextId === challengeId) return;
    challengeId = nextId;
    validationError = "";
  });

  function deny(event?: Event) {
    event?.preventDefault();
    if (!working && challenge) onrespond({ decision: "deny" });
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (working || !challenge) return;
    if (!fieldValid) {
      validationError = tr("human_invalid", lang);
      return;
    }
    validationError = "";
    onrespond({ decision: "submit", value: fieldValue });
  }
</script>

{#if challenge && request}
  <PromptDialog
    bind:open
    {kicker}
    title={request.title}
    titleId="human-request-title"
    lead={request.description}
    size="md"
    oncancel={deny}
    onsubmit={submit}
  >
    <AssistantHumanRequestBody
      {challenge}
      {lang}
      {validationError}
      bind:fieldValue
      bind:fieldValid
    />
    {#snippet footer()}
      <Button type="button" variant="secondary" disabled={working} onclick={deny}>{tr("human_cancel", lang)}</Button>
      <Button type="submit" disabled={working}>{primaryLabel}</Button>
    {/snippet}
  </PromptDialog>
{/if}
