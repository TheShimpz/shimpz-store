<script lang="ts">
  import { onMount } from "svelte";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import HudIcon from "$lib/components/HudIcon.svelte";

  type ProviderId = "claude-code" | "codex";
  type AuthType = "api_key" | "oauth";
  type LoadState = "loading" | "ready" | "error";
  type BrainRecord = {
    provider: ProviderId;
    auth_type: AuthType;
    status: "configured" | "revoking";
  };

  let { lang }: { lang: Locale } = $props();

  const providers: { id: ProviderId; title: string; note: string }[] = [
    { id: "claude-code", title: "Claude Code", note: "Anthropic" },
    { id: "codex", title: "Codex", note: "OpenAI" },
  ];

  let loadState = $state<LoadState>("loading");
  let brains = $state<BrainRecord[]>([]);
  let capsules = $state<any[]>([]);
  let capsulesLoaded = $state(false);
  let provider = $state<ProviderId>("claude-code");
  let authType = $state<AuthType>("api_key");
  let step = $state<1 | 2 | 3 | 4>(1);
  let secret = $state("");
  let reveal = $state(false);
  let busy = $state(false);
  let message = $state("");
  let messageTone = $state<"" | "error" | "success">("");
  let confirmRemove = $state<ProviderId | "">("");
  let fieldError = $state("");

  const matchingCapsules = $derived(
    capsules.filter((capsule) => (capsule.brain ?? "claude-code") === provider),
  );

  function recordFor(id: ProviderId) {
    return brains.find((entry) => entry.provider === id);
  }

  function statusLabel(id: ProviderId) {
    const record = recordFor(id);
    if (record?.status === "revoking") return lang === "pt" ? "Remoção pendente" : "Removal pending";
    return tr(record?.status === "configured" ? "brain_configured" : "brain_not_configured", lang);
  }

  async function load({ preserveMessage = false }: { preserveMessage?: boolean } = {}) {
    loadState = "loading";
    if (!preserveMessage) message = "";
    try {
      const [brainsResponse, capsulesResponse] = await Promise.all([
        fetch("/api/brains"),
        fetch("/api/capsules").catch(() => null),
      ]);
      const brainResult = await brainsResponse.json().catch(() => null);
      if (!brainsResponse.ok || !Array.isArray(brainResult?.brains)) throw new Error("brains unavailable");
      brains = brainResult.brains;
      if (capsulesResponse?.ok) {
        const capsuleResult = await capsulesResponse.json().catch(() => ({}));
        capsules = Array.isArray(capsuleResult?.capsules) ? capsuleResult.capsules : [];
        capsulesLoaded = true;
      } else {
        capsules = [];
        capsulesLoaded = false;
      }
      loadState = "ready";
    } catch {
      capsulesLoaded = false;
      loadState = "error";
    }
  }

  function chooseProvider(id: ProviderId) {
    provider = id;
    authType = recordFor(id)?.auth_type ?? "api_key";
    secret = "";
    reveal = false;
    fieldError = "";
    message = "";
    step = 2;
  }

  function chooseAuth(value: AuthType) {
    authType = value;
    secret = "";
    reveal = false;
    fieldError = "";
  }

  function validateCredential() {
    const value = secret.trim();
    if (!value) return tr("brain_secret_required", lang);
    if (provider === "codex" && authType === "oauth") {
      try {
        const parsed = JSON.parse(value);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not an object");
      } catch {
        return tr("brain_codex_oauth_invalid", lang);
      }
    }
    return "";
  }

  async function applyToCapsules() {
    if (!capsulesLoaded) return { total: -1, applied: 0 };
    let applied = 0;
    for (let index = 0; index < matchingCapsules.length; index += 4) {
      const batch = matchingCapsules.slice(index, index + 4);
      const results = await Promise.all(
        batch.map((capsule) =>
          fetch(`/api/capsules/${capsule.id}/brain/configure`, { method: "POST" })
            .then((response) => response.ok)
            .catch(() => false),
        ),
      );
      applied += results.filter(Boolean).length;
    }
    return { total: matchingCapsules.length, applied };
  }

  function resultText(total: number, applied: number) {
    if (total < 0) return tr("brain_saved_apply_failed", lang);
    if (total === 0) {
      return lang === "pt"
        ? "Credencial cifrada. Nenhuma Cápsula existente usa este Cérebro ainda."
        : "Credential sealed. No existing Capsule uses this Brain yet.";
    }
    if (total === applied) {
      return lang === "pt"
        ? `Credencial cifrada e aplicada a ${applied} ${applied === 1 ? "Cápsula" : "Cápsulas"}.`
        : `Credential sealed and applied to ${applied} ${applied === 1 ? "Capsule" : "Capsules"}.`;
    }
    return lang === "pt"
      ? `Credencial cifrada, mas aplicada a ${applied} de ${total} Cápsulas.`
      : `Credential sealed, but applied to ${applied} of ${total} Capsules.`;
  }

  async function save() {
    if (busy) return;
    fieldError = validateCredential();
    if (fieldError) return;
    busy = true;
    message = "";
    messageTone = "";
    try {
      const response = await fetch(`/api/brains/${provider}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auth_type: authType, secret: secret.trim() }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        message = result.detail ?? result.error ?? (lang === "pt" ? "Não foi possível salvar a credencial." : "Could not save the credential.");
        messageTone = "error";
        return;
      }
      secret = "";
      reveal = false;
      const applied = await applyToCapsules();
      await load({ preserveMessage: true });
      message = resultText(applied.total, applied.applied);
      messageTone = applied.total >= 0 && applied.total === applied.applied ? "success" : "error";
      step = 4;
    } finally {
      busy = false;
    }
  }

  async function remove(id: ProviderId) {
    if (busy) return;
    const existing = recordFor(id);
    if (existing?.status !== "revoking" && confirmRemove !== id) {
      confirmRemove = id;
      return;
    }
    busy = true;
    message = "";
    messageTone = "";
    try {
      const response = await fetch(`/api/brains/${id}`, { method: "DELETE" }).catch(() => null);
      const result = await response?.json().catch(() => ({}));
      if (!response?.ok) {
        message = result?.detail ?? result?.error ?? (lang === "pt" ? "Não foi possível remover a credencial." : "Could not remove the credential.");
        messageTone = "error";
      } else {
        message = tr("brain_removed", lang);
        messageTone = "success";
      }
      confirmRemove = "";
      await load({ preserveMessage: true });
      step = 1;
    } finally {
      busy = false;
    }
  }

  onMount(load);
</script>

<section class="brain-console panel" aria-labelledby="brain-wizard-title">
  <header class="console-head">
    <div class="console-mark"><HudIcon name="brain" size={25} /></div>
    <div>
      <p class="kicker">{tr("account_brains", lang)}</p>
      <h2 id="brain-wizard-title">{tr("brain_wizard_title", lang)}</h2>
      <p>{tr("brain_wizard_lead", lang)}</p>
    </div>
  </header>

  {#if loadState === "loading"}
    <p class="loading" role="status">{tr("loading", lang)}</p>
  {:else if loadState === "error"}
    <div class="notice notice-error state-notice" role="alert">
      <span>{tr("brain_load_failed", lang)}</span>
      <button class="btn-ghost compact" type="button" onclick={() => load()}>
        <HudIcon name="retry" size={15} /> {tr("brain_retry_load", lang)}
      </button>
    </div>
  {:else}
    <ol class="stepper" aria-label={tr("brain_wizard_title", lang)}>
      {#each [tr("brain_step_provider", lang), tr("brain_step_access", lang), tr("brain_step_credential", lang)] as label, index (label)}
        <li class:active={step === index + 1} class:complete={step > index + 1} aria-current={step === index + 1 ? "step" : undefined}>
          <span>{String(index + 1).padStart(2, "0")}</span>{label}
        </li>
      {/each}
    </ol>

    <div class="stage">
      {#if step === 1}
        <div class="stage-copy">
          <h3>{tr("brain_choose_provider", lang)}</h3>
          <p>{tr("brain_choose_provider_help", lang)}</p>
        </div>
        <div class="option-grid">
          {#each providers as option (option.id)}
            <button class="option" type="button" onclick={() => chooseProvider(option.id)}>
              <span class="option-icon"><HudIcon name="brain" size={22} /></span>
              <span class="option-copy"><strong>{option.title}</strong><small>{option.note}</small></span>
              <span class="badge" class:ready={recordFor(option.id)?.status === "configured"}>{statusLabel(option.id)}</span>
            </button>
          {/each}
        </div>
      {:else if step === 2}
        <div class="stage-copy">
          <p class="selection">{providers.find((entry) => entry.id === provider)?.title}</p>
          <h3>{tr("brain_choose_auth", lang)}</h3>
          <p>{tr("brain_choose_auth_help", lang)}</p>
        </div>
        <div class="option-grid">
          <button class="option" class:selected={authType === "api_key"} type="button" onclick={() => chooseAuth("api_key")}>
            <span class="option-icon"><HudIcon name="key" size={22} /></span>
            <span class="option-copy"><strong>{tr("brain_api_key", lang)}</strong><small>{tr("brain_api_key_desc", lang)}</small></span>
          </button>
          <button class="option" class:selected={authType === "oauth"} type="button" onclick={() => chooseAuth("oauth")}>
            <span class="option-icon"><HudIcon name="shield" size={22} /></span>
            <span class="option-copy"><strong>{tr("brain_oauth", lang)}</strong><small>{tr("brain_oauth_desc", lang)}</small></span>
          </button>
        </div>
        <div class="stage-actions">
          <button class="btn-ghost compact" type="button" onclick={() => (step = 1)}>{tr("brain_back", lang)}</button>
          <button class="btn-primary compact" type="button" onclick={() => (step = 3)}>{tr("brain_continue", lang)} →</button>
        </div>
      {:else if step === 3}
        <div class="stage-copy">
          <p class="selection">{providers.find((entry) => entry.id === provider)?.title} // {tr(authType === "oauth" ? "brain_oauth" : "brain_api_key", lang)}</p>
          <h3>{tr("brain_credential_title", lang)}</h3>
          <p>{tr("brain_credential_review", lang)}</p>
        </div>
        <label class="credential-field">
          <span class="kicker">{tr("brain_secret", lang)}</span>
          {#if authType === "api_key"}
            <span class="secret-input">
              <input
                class="field"
                type={reveal ? "text" : "password"}
                autocomplete="off"
                spellcheck="false"
                bind:value={secret}
                oninput={() => (fieldError = "")} />
              <button type="button" onclick={() => (reveal = !reveal)}>{tr(reveal ? "password_hide" : "password_show", lang)}</button>
            </span>
          {:else}
            <textarea class="field" rows="5" autocomplete="off" spellcheck="false" bind:value={secret} oninput={() => (fieldError = "")}></textarea>
          {/if}
          <small>{tr(authType === "oauth" ? "brain_secret_oauth_help" : "brain_secret_api_help", lang)}</small>
        </label>
        <div class="review-row">
          <HudIcon name="capsule" size={18} />
          <span>
            {#if capsulesLoaded}
              {lang === "pt"
                ? `${matchingCapsules.length} ${matchingCapsules.length === 1 ? "Cápsula usa" : "Cápsulas usam"} este Cérebro`
                : `${matchingCapsules.length} ${matchingCapsules.length === 1 ? "Capsule uses" : "Capsules use"} this Brain`}
            {:else}
              {tr("brain_load_failed", lang)}
            {/if}
          </span>
        </div>
        {#if fieldError}<p class="field-error" role="alert">{fieldError}</p>{/if}
        {#if message}<p class="notice state-notice" class:notice-error={messageTone === "error"} role={messageTone === "error" ? "alert" : "status"}>{message}</p>{/if}
        <div class="stage-actions">
          <button class="btn-ghost compact" type="button" disabled={busy} onclick={() => (step = 2)}>{tr("brain_back", lang)}</button>
          <button class="btn-primary compact" type="button" disabled={busy || !secret.trim()} onclick={save}>
            {#if busy}{tr("brain_saving", lang)}{:else}<HudIcon name="shield" size={16} /> {tr("brain_save", lang)}{/if}
          </button>
        </div>
      {:else}
        <div class="done-mark"><HudIcon name="check" size={30} /></div>
        <div class="stage-copy done-copy">
          <h3>{tr("brain_done_title", lang)}</h3>
          <p>{tr("brain_done_body", lang)}</p>
        </div>
        {#if message}<p class="notice state-notice" class:notice-error={messageTone === "error"} class:notice-success={messageTone === "success"} role={messageTone === "error" ? "alert" : "status"}>{message}</p>{/if}
        <div class="stage-actions done-actions">
          <button class="btn-ghost compact" type="button" onclick={() => { message = ""; step = 1; }}>{tr("brain_reconfigure", lang)}</button>
          <a class="btn-primary compact" href={u.chat(lang)}>{tr("nav_chat", lang)} →</a>
        </div>
      {/if}
    </div>

    <div class="configured-list">
      <h3>{tr("brain_configured_list", lang)}</h3>
      {#if brains.length === 0}
        <p>{tr("brain_none_configured", lang)}</p>
      {:else}
        {#each brains as entry (entry.provider)}
          <div class="configured-row">
            <span class="configured-icon"><HudIcon name="brain" size={18} /></span>
            <span class="configured-name">
              <strong>{providers.find((option) => option.id === entry.provider)?.title}</strong>
              <small>{tr(entry.auth_type === "oauth" ? "brain_oauth" : "brain_api_key", lang)}</small>
            </span>
            <span class="badge" class:ready={entry.status === "configured"}>{statusLabel(entry.provider)}</span>
            <button class="btn-ghost row-action" type="button" disabled={busy || entry.status === "revoking"} onclick={() => chooseProvider(entry.provider)}>{tr("brain_reconfigure", lang)}</button>
            <button class="btn-danger row-action" type="button" disabled={busy} onclick={() => remove(entry.provider)}>
              {entry.status === "revoking" ? (lang === "pt" ? "Tentar remoção" : "Retry removal") : tr("brain_remove", lang)}
            </button>
            {#if confirmRemove === entry.provider && entry.status !== "revoking"}
              <div class="remove-confirm">
                <span>{tr("brain_remove_confirm", lang)}</span>
                <button class="btn-danger row-action" type="button" onclick={() => remove(entry.provider)}>{tr("brain_remove", lang)}</button>
                <button class="btn-ghost row-action" type="button" onclick={() => (confirmRemove = "")}>{tr("brain_cancel", lang)}</button>
              </div>
            {/if}
          </div>
        {/each}
      {/if}
      {#if message && step !== 3 && step !== 4}
        <p class="notice state-notice" class:notice-error={messageTone === "error"} class:notice-success={messageTone === "success"} role={messageTone === "error" ? "alert" : "status"}>{message}</p>
      {/if}
    </div>
  {/if}
</section>

<style>
  .brain-console { padding: clamp(1.1rem, 3vw, 1.6rem); }
  .console-head { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 1rem; align-items: start; }
  .console-mark,
  .option-icon,
  .configured-icon,
  .done-mark {
    display: grid;
    place-items: center;
    color: var(--color-cyan);
    background: #000;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  }
  .console-mark { width: 3.1rem; height: 3.1rem; }
  .console-head h2 { margin: 0.15rem 0 0; font-size: clamp(1.35rem, 3vw, 1.8rem); }
  .console-head p:last-child { max-width: 42rem; margin: 0.4rem 0 0; color: var(--color-muted); font-size: 0.85rem; line-height: 1.6; }
  .loading { margin: 2rem 0 0; color: var(--color-muted); }
  .stepper { display: grid; grid-template-columns: repeat(3, 1fr); margin: 1.5rem 0 0; padding: 0; list-style: none; }
  .stepper li { display: flex; min-width: 0; align-items: center; gap: 0.5rem; border-bottom: 1px solid var(--color-border); padding: 0.65rem 0.35rem; color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.62rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
  .stepper li span { color: var(--color-muted-2); }
  .stepper li.active { border-color: var(--color-cyan); color: var(--color-fg); box-shadow: 0 1px 0 rgba(0, 240, 255, 0.3); }
  .stepper li.active span,
  .stepper li.complete span { color: var(--color-cyan); }
  .stage { min-height: 20rem; padding: clamp(1.2rem, 3vw, 1.8rem) 0 1.25rem; }
  .stage-copy h3 { margin: 0; font-size: clamp(1.15rem, 2.5vw, 1.45rem); }
  .stage-copy > p:not(.selection) { max-width: 42rem; margin: 0.45rem 0 0; color: var(--color-muted); font-size: 0.85rem; }
  .selection { margin: 0 0 0.45rem; color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
  .option-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; margin-top: 1.15rem; }
  .option { display: grid; min-width: 0; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.8rem; border: 0; padding: 0.9rem; background: #000; box-shadow: inset 0 0 0 1px var(--color-border); color: var(--color-fg); cursor: pointer; text-align: left; clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px); }
  .option:hover,
  .option.selected { box-shadow: inset 0 0 0 1px var(--color-cyan); }
  .option-icon { width: 2.5rem; height: 2.5rem; }
  .option-copy { min-width: 0; }
  .option-copy strong,
  .option-copy small { display: block; }
  .option-copy strong { font-family: var(--font-mono); font-size: 0.88rem; }
  .option-copy small { margin-top: 0.2rem; color: var(--color-muted); font-size: 0.68rem; line-height: 1.45; }
  .badge.ready { color: var(--color-green); }
  .stage-actions { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.65rem; margin-top: 1.15rem; }
  .compact { min-height: 2.5rem; padding: 0.55rem 0.85rem; font-size: 0.7rem; }
  .credential-field { display: block; margin-top: 1.1rem; }
  .credential-field small { display: block; margin-top: 0.45rem; color: var(--color-muted); font-size: 0.7rem; }
  .secret-input { position: relative; display: block; margin-top: 0.45rem; }
  .secret-input input { padding-right: 5.5rem; }
  .secret-input button { position: absolute; top: 50%; right: 0.65rem; border: 0; padding: 0.4rem; background: transparent; color: var(--color-cyan); cursor: pointer; font-family: var(--font-mono); font-size: 0.65rem; text-transform: uppercase; transform: translateY(-50%); }
  textarea.field { margin-top: 0.45rem; resize: vertical; font-family: var(--font-mono); font-size: 0.76rem; }
  .review-row { display: flex; align-items: center; gap: 0.55rem; margin-top: 0.9rem; color: var(--color-muted); font-size: 0.75rem; }
  .review-row :global(svg) { color: var(--color-cyan); }
  .field-error { margin: 0.65rem 0 0; color: var(--color-danger); font-size: 0.75rem; }
  .state-notice { margin-top: 0.9rem; padding: 0.75rem 0.9rem; font-size: 0.75rem; }
  .state-notice:not(p) { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.75rem; }
  .done-mark { width: 3.5rem; height: 3.5rem; margin: 0 auto; color: var(--color-green); }
  .done-copy { margin-top: 0.9rem; text-align: center; }
  .done-copy p { margin-inline: auto !important; }
  .done-actions { justify-content: center; }
  .configured-list { border-top: 1px solid var(--color-border); padding-top: 1rem; }
  .configured-list > h3 { margin: 0 0 0.7rem; color: var(--color-muted); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }
  .configured-list > p:not(.notice) { margin: 0; color: var(--color-muted); font-size: 0.8rem; }
  .configured-row { position: relative; display: grid; grid-template-columns: auto minmax(7rem, 1fr) auto auto auto; align-items: center; gap: 0.55rem; border-top: 1px solid var(--color-border); padding: 0.65rem 0; }
  .configured-row:first-of-type { border-top: 0; }
  .configured-icon { width: 2rem; height: 2rem; }
  .configured-name strong,
  .configured-name small { display: block; }
  .configured-name strong { font-family: var(--font-mono); font-size: 0.8rem; }
  .configured-name small { color: var(--color-muted); font-size: 0.65rem; }
  .row-action { min-height: 2rem; padding: 0.35rem 0.55rem; font-size: 0.58rem; }
  .remove-confirm { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: center; gap: 0.55rem; padding: 0.7rem; background: color-mix(in oklab, var(--color-danger) 7%, #000); box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-danger) 40%, var(--color-border)); color: var(--color-danger); font-size: 0.72rem; }
  .remove-confirm span { flex: 1 1 18rem; }

  @media (max-width: 720px) {
    .option-grid { grid-template-columns: 1fr; }
    .configured-row { grid-template-columns: auto minmax(0, 1fr) auto; }
    .configured-row > .row-action { grid-row: 2; }
    .configured-row > .row-action:first-of-type { grid-column: 2; }
  }
  @media (max-width: 480px) {
    .console-head { grid-template-columns: 1fr; }
    .stepper li { align-items: flex-start; flex-direction: column; gap: 0.1rem; }
    .option { grid-template-columns: auto minmax(0, 1fr); }
    .option .badge { grid-column: 2; justify-self: start; }
  }
</style>
