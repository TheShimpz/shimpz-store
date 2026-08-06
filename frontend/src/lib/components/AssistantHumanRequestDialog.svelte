<script lang="ts">
  import {
    Button,
    Card,
    CheckboxField,
    Notice,
    PromptDialog,
    RadioField,
    SelectField,
    TextAreaField,
    TextField,
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
  let textValue = $state("");
  let singleValue = $state("");
  let selectedValues = $state<string[]>([]);
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

  $effect(() => {
    const nextId = challenge?.challenge_id ?? "";
    if (nextId === challengeId) return;
    challengeId = nextId;
    textValue = "";
    singleValue = "";
    selectedValues = [];
    validationError = "";
  });

  function deny(event?: Event) {
    event?.preventDefault();
    if (!working && challenge) onrespond({ decision: "deny" });
  }

  function toggle(value: string, checked: boolean) {
    selectedValues = checked
      ? [...selectedValues, value]
      : selectedValues.filter((item) => item !== value);
  }

  function responseValue() {
    if (kind === "approval") return true;
    if (kind === "input:select" || kind === "input:choice") return singleValue;
    if (kind === "input:choices") return selectedValues;
    if (kind === "auth:phishing-resistant") return "passkey";
    return textValue;
  }

  function valid(value: any) {
    if (kind === "approval") return value === true;
    if (kind === "input:select" || kind === "input:choice") {
      return value !== "" || request.required === false;
    }
    if (kind === "input:choices") {
      return value.length >= request.min_selections && value.length <= request.max_selections;
    }
    if (kind === "auth:phishing-resistant") return true;
    if (isAuth) return typeof value === "string" && value.length > 0;
    return typeof value === "string" &&
      value.length >= request.min_length &&
      value.length <= request.max_length &&
      (request.required === false || value.length > 0);
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (working || !challenge) return;
    const value = responseValue();
    if (!valid(value)) {
      validationError = tr("human_invalid", lang);
      return;
    }
    validationError = "";
    onrespond({ decision: "submit", value });
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

    {#if kind === "input:text" || kind === "input:password" || kind === "input:phone"}
      {#if kind === "input:password"}<Notice variant="warning">{tr("human_third_party_secret", lang)}</Notice>{/if}
      <TextField
        id="human-request-value"
        label={`${request.label} · ${tr(request.required ? "human_required" : "human_optional", lang)}`}
        type={kind === "input:password" ? "password" : kind === "input:phone" ? "tel" : "text"}
        inputmode={kind === "input:phone" ? "tel" : undefined}
        autocomplete={kind === "input:phone" ? "tel" : "off"}
        spellcheck={kind === "input:password" ? "false" : undefined}
        placeholder={request.placeholder ?? undefined}
        minlength={request.min_length}
        maxlength={request.max_length}
        required={request.required}
        bind:value={textValue}
      />
    {:else if kind === "input:textarea"}
      <TextAreaField
        id="human-request-value"
        label={`${request.label} · ${tr(request.required ? "human_required" : "human_optional", lang)}`}
        placeholder={request.placeholder ?? undefined}
        minlength={request.min_length}
        maxlength={request.max_length}
        required={request.required}
        rows={6}
        bind:value={textValue}
      />
    {:else if kind === "input:select"}
      <SelectField
        id="human-request-value"
        label={`${request.label} · ${tr(request.required ? "human_required" : "human_optional", lang)}`}
        placeholder={tr("human_choose", lang)}
        options={request.options}
        required={request.required}
        bind:value={singleValue}
      />
    {:else if kind === "input:choice"}
      <fieldset>
        <legend>{request.label} · {tr(request.required ? "human_required" : "human_optional", lang)}</legend>
        {#each request.options as option (option.value)}
          <RadioField
            id={`human-request-${option.value}`}
            name="human-request-choice"
            optionValue={option.value}
            label={option.label}
            description={option.description ?? undefined}
            bind:value={singleValue}
          />
        {/each}
      </fieldset>
    {:else if kind === "input:choices"}
      <fieldset>
        <legend>{request.label} · {tr(request.required ? "human_required" : "human_optional", lang)}</legend>
        <p class="field-hint">{tr("human_selection_hint", lang)} {request.min_selections}–{request.max_selections}</p>
        {#each request.options as option (option.value)}
          <CheckboxField
            id={`human-request-${option.value}`}
            label={option.label}
            hint={option.description ?? undefined}
            checked={selectedValues.includes(option.value)}
            onchange={(event) => toggle(option.value, event.currentTarget.checked)}
          />
        {/each}
      </fieldset>
    {:else if kind === "auth:reauth"}
      <Notice variant="warning">{tr("human_reauth_hint", lang)}</Notice>
      <TextField
        id="human-request-auth"
        label={tr("human_password_label", lang)}
        type="password"
        autocomplete="current-password"
        required
        maxlength={4096}
        bind:value={textValue}
      />
    {:else if kind === "auth:second-factor"}
      <Notice variant="warning">{tr("human_totp_hint", lang)}</Notice>
      <TextField
        id="human-request-auth"
        label={tr("human_totp_label", lang)}
        type="text"
        inputmode="numeric"
        autocomplete="one-time-code"
        placeholder={tr("human_totp_placeholder", lang)}
        required
        maxlength={16}
        bind:value={textValue}
      />
    {:else if kind === "auth:phishing-resistant"}
      <Notice variant="warning">{tr("human_passkey_hint", lang)}</Notice>
    {/if}

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
  fieldset { display: grid; gap: var(--shimpz-space-2); margin: 0; border: 0; padding: 0; }
  legend { margin-bottom: var(--shimpz-space-1); padding: 0; color: var(--shimpz-color-text); font: 600 0.7rem/1.2 var(--shimpz-font-mono); letter-spacing: 0.07em; text-transform: uppercase; }
  .field-hint { margin: 0 0 var(--shimpz-space-1); color: var(--shimpz-color-text-dim); font-size: 0.72rem; }
  @media (max-width: 520px) { :global(.request-origin > [data-slot="card-content"]) { grid-template-columns: 1fr; } }
</style>
