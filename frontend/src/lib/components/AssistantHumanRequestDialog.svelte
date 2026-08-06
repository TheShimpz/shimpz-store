<script lang="ts">
  import {
    Button,
    Card,
    Notice,
    PowerRequestFields,
    PromptDialog,
  } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
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
  const isAuth = $derived(kind.startsWith("auth:"));
  const isInput = $derived(kind.startsWith("input:"));
  const kicker = $derived(
    tr(isAuth ? "human_auth_kicker" : isInput ? "human_input_kicker" : "human_approval_kicker", lang),
  );
  const primaryLabel = $derived(
    tr(
      kind === "approval"
        ? "human_approve"
        : kind === "auth:phishing-resistant"
          ? "human_passkey"
          : isAuth
            ? "human_authorize"
            : "human_submit",
      lang,
    ),
  );
  const fieldLabels = $derived({
    required: tr("human_required", lang),
    optional: tr("human_optional", lang),
    chooseOption: tr("human_choose", lang),
    selectionHint: `${tr("human_selection_hint", lang)} ${request?.min_selections ?? 0}–${request?.max_selections ?? 0}`,
    thirdPartySecret: tr("human_third_party_secret", lang),
    reauthHint: tr("human_reauth_hint", lang),
    reauthLabel: tr("human_password_label", lang),
    secondFactorHint: tr("human_totp_hint", lang),
    secondFactorLabel: tr("human_totp_label", lang),
    secondFactorPlaceholder: tr("human_totp_placeholder", lang),
    passkeyHint: tr("human_passkey_hint", lang),
  });

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
    <p class="paused">
      {tr("human_paused", lang)}
      <span>{tr("human_expires", lang)} {challenge.expires_in} {tr("human_seconds", lang)}.</span>
    </p>
    <Card class="request-origin" padding="compact">
      <div><span>{tr("human_assistant", lang)}</span><strong>{challenge.assistant.name}</strong><code>{challenge.assistant.id}</code></div>
      <div><span>{tr("human_power", lang)}</span><strong>{challenge.power.summary}</strong><code>{challenge.power.id}</code></div>
    </Card>

    <PowerRequestFields
      {request}
      resetKey={challenge.challenge_id}
      labels={fieldLabels}
      bind:value={fieldValue}
      bind:valid={fieldValid}
    />

    {#if validationError}<Notice variant="error">{validationError}</Notice>{/if}
    {#snippet footer()}
      <Button type="button" variant="secondary" disabled={working} onclick={deny}>{tr("human_cancel", lang)}</Button>
      <Button type="submit" disabled={working}>{primaryLabel}</Button>
    {/snippet}
  </PromptDialog>
{/if}

<style>
  .paused { margin: 0; color: var(--shimpz-color-text-dim); font-size: 0.72rem; line-height: 1.5; }
  .paused span { color: var(--shimpz-color-cyan); font-family: var(--shimpz-font-mono); }
  :global(.request-origin > [data-slot="card-content"]) { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--shimpz-space-4); }
  :global(.request-origin [data-slot="card-content"] > div) { display: grid; min-width: 0; gap: 0.18rem; }
  :global(.request-origin span) { color: var(--shimpz-color-text-faint); font: 600 0.58rem/1.2 var(--shimpz-font-mono); letter-spacing: 0.08em; text-transform: uppercase; }
  :global(.request-origin strong) { overflow: hidden; font-size: 0.78rem; line-height: 1.4; text-overflow: ellipsis; }
  :global(.request-origin code) { overflow: hidden; color: var(--shimpz-color-cyan); font-size: 0.6rem; text-overflow: ellipsis; }
  @media (max-width: 520px) { :global(.request-origin > [data-slot="card-content"]) { grid-template-columns: 1fr; } }
</style>
