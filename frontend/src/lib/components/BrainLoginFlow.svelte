<script lang="ts">
  import { onDestroy } from "svelte";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import {
    brainLoginEndpoints,
    parseBrainLoginChallenge,
    parseBrainLoginStatus,
  } from "$lib/brainLogin.js";

  type Provider = "claude-code" | "codex";
  type Phase = "idle" | "starting" | "authorize" | "device" | "checking" | "done" | "error";
  type Challenge =
    | { kind: "authorization_code"; url: string }
    | { kind: "device"; url: string; userCode: string };

  let {
    lang,
    capsuleId,
    provider,
    oncomplete = () => {},
  }: {
    lang: Locale;
    capsuleId: string;
    provider: Provider;
    oncomplete?: () => void | Promise<void>;
  } = $props();

  let phase = $state<Phase>("idle");
  let challenge = $state<Challenge | null>(null);
  let authorizationCode = $state("");
  let error = $state("");
  let copied = $state(false);
  let attempt = 0;
  let context = "";
  let contextCapsule = "";
  let contextProvider: Provider = "claude-code";

  function cancelAbandonedDevice(id: string, selectedProvider: Provider) {
    if (selectedProvider !== "codex" || !id || challenge?.kind !== "device") return;
    try {
      void fetch(brainLoginEndpoints(id).cancel, { method: "POST", keepalive: true }).catch(() => null);
    } catch {
      // An invalid stale context has no safe endpoint to call.
    }
  }

  $effect(() => {
    const next = `${capsuleId}:${provider}`;
    if (next !== context) {
      cancelAbandonedDevice(contextCapsule, contextProvider);
      context = next;
      contextCapsule = capsuleId;
      contextProvider = provider;
      attempt += 1;
      phase = "idle";
      challenge = null;
      authorizationCode = "";
      error = "";
      copied = false;
    }
  });

  async function json(response: Response | null) {
    return response?.json().catch(() => ({})) ?? {};
  }

  function fail(message: unknown, fallback: string) {
    error = typeof message === "string" && message.trim() ? message.slice(0, 300) : fallback;
    phase = "error";
  }

  async function cancelDevice(resetToIdle = true) {
    if (provider !== "codex" || !capsuleId) return false;
    let endpoints;
    try {
      endpoints = brainLoginEndpoints(capsuleId);
    } catch (caught) {
      fail(caught instanceof Error ? caught.message : "", tr("brain_login_cancel_failed", lang));
      return false;
    }
    const cancelAttempt = ++attempt;
    phase = "checking";
    const response = await fetch(endpoints.cancel, { method: "POST" }).catch(() => null);
    const payload = await json(response);
    if (cancelAttempt !== attempt) return false;
    if (!response?.ok) {
      fail(payload?.detail ?? payload?.error, tr("brain_login_cancel_failed", lang));
      return false;
    }
    challenge = null;
    authorizationCode = "";
    copied = false;
    error = "";
    if (resetToIdle) phase = "idle";
    return true;
  }

  async function pollStatus(endpoints: ReturnType<typeof brainLoginEndpoints>, activeAttempt: number, rounds: number) {
    let lastError = "";
    for (let index = 0; index < rounds && activeAttempt === attempt; index += 1) {
      await new Promise((done) => setTimeout(done, 1200));
      if (activeAttempt !== attempt) return;
      const response = await fetch(endpoints.status, { cache: "no-store" }).catch(() => null);
      const payload = await json(response);
      if (!response?.ok) {
        fail(payload?.detail ?? payload?.error, tr("brain_login_status_failed", lang));
        return;
      }
      const status = parseBrainLoginStatus(payload);
      lastError = status.lastError || lastError;
      if (status.loggedIn) {
        challenge = null;
        phase = "done";
        await oncomplete();
        return;
      }
      if (status.lastError || ["failed", "cancelled", "timeout"].includes(status.state)) {
        fail(status.lastError, tr("brain_code_err", lang));
        return;
      }
    }
    if (activeAttempt === attempt && provider === "codex") {
      const cancelled = await cancelDevice(false);
      if (cancelled) fail(lastError, tr("brain_login_timeout", lang));
    } else if (activeAttempt === attempt) {
      fail(lastError, tr("brain_login_timeout", lang));
    }
  }

  async function start() {
    if (!capsuleId || phase === "starting" || phase === "checking") return;
    if (provider === "codex" && (phase === "error" || challenge?.kind === "device") && !(await cancelDevice())) return;
    let endpoints;
    try {
      endpoints = brainLoginEndpoints(capsuleId);
    } catch (caught) {
      fail(caught instanceof Error ? caught.message : "", tr("brain_login_start_failed", lang));
      return;
    }
    const activeAttempt = ++attempt;
    phase = "starting";
    challenge = null;
    authorizationCode = "";
    error = "";
    copied = false;
    const response = await fetch(endpoints.start, { method: "POST" }).catch(() => null);
    const payload = await json(response);
    if (activeAttempt !== attempt) return;
    if (!response?.ok) {
      fail(payload?.detail ?? payload?.error, tr("brain_login_start_failed", lang));
      return;
    }
    for (let index = 0; index < 50 && activeAttempt === attempt; index += 1) {
      await new Promise((done) => setTimeout(done, 1200));
      if (activeAttempt !== attempt) return;
      const challengeResponse = await fetch(endpoints.challenge, { cache: "no-store" }).catch(() => null);
      const challengePayload = await json(challengeResponse);
      if (activeAttempt !== attempt) return;
      if (!challengeResponse?.ok) {
        fail(challengePayload?.detail ?? challengePayload?.error, tr("brain_login_status_failed", lang));
        return;
      }
      const parsed = parseBrainLoginChallenge(provider, challengePayload);
      if (parsed) {
        challenge = parsed;
        phase = parsed.kind === "device" ? "device" : "authorize";
        if (parsed.kind === "device") void pollStatus(endpoints, activeAttempt, 800);
        return;
      }
      if (challengePayload?.url) {
        if (provider === "codex") {
          const cancelled = await cancelDevice(false);
          if (cancelled) fail("", tr("brain_login_challenge_invalid", lang));
        } else {
          fail("", tr("brain_login_challenge_invalid", lang));
        }
        return;
      }
    }
    if (activeAttempt === attempt && provider === "codex") {
      const cancelled = await cancelDevice(false);
      if (cancelled) fail("", tr("brain_login_timeout", lang));
    } else if (activeAttempt === attempt) {
      fail("", tr("brain_login_timeout", lang));
    }
  }

  async function submitCode() {
    if (provider !== "claude-code" || challenge?.kind !== "authorization_code" || !authorizationCode.trim()) return;
    const activeAttempt = attempt;
    const endpoints = brainLoginEndpoints(capsuleId);
    phase = "checking";
    error = "";
    const response = await fetch(endpoints.code, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: authorizationCode.trim() }),
    }).catch(() => null);
    const payload = await json(response);
    if (activeAttempt !== attempt) return;
    if (!response?.ok || payload?.ok !== true) {
      fail(payload?.detail ?? payload?.error, tr("brain_code_err", lang));
      return;
    }
    await pollStatus(endpoints, activeAttempt, 10);
  }

  async function copyUserCode() {
    if (challenge?.kind !== "device") return;
    try {
      await navigator.clipboard.writeText(challenge.userCode);
      copied = true;
    } catch {
      copied = false;
    }
  }

  onDestroy(() => {
    cancelAbandonedDevice(contextCapsule, contextProvider);
    attempt += 1;
  });
</script>

<div class="brain-login" aria-live="polite">
  {#if phase === "idle" || phase === "error"}
    {#if phase === "error"}<p class="notice notice-error login-error" role="alert">{error}</p>{/if}
    <button class="btn-ghost login-start" type="button" disabled={!capsuleId} onclick={start}>
      {tr(provider === "codex" ? "brain_codex_device_start" : "brain_configure", lang)}
    </button>
  {:else if phase === "starting" || phase === "checking"}
    <p class="login-progress"><span class="loading-pulse" aria-hidden="true"></span>{tr(phase === "starting" ? "brain_starting" : "brain_login_checking", lang)}</p>
  {:else if phase === "authorize" && challenge?.kind === "authorization_code"}
    <div class="login-steps">
      <a class="btn-primary" href={challenge.url} target="_blank" rel="noopener noreferrer">{tr("brain_open_url", lang)} ↗</a>
      <input
        class="field field-sm"
        placeholder={tr("brain_paste_code", lang)}
        autocomplete="off"
        spellcheck="false"
        bind:value={authorizationCode}
        onkeydown={(event) => event.key === "Enter" && !event.isComposing && submitCode()} />
      <button class="btn-ghost" type="button" disabled={!authorizationCode.trim()} onclick={submitCode}>{tr("brain_submit_code", lang)}</button>
    </div>
  {:else if phase === "device" && challenge?.kind === "device"}
    <div class="login-steps">
      <a class="btn-primary" href={challenge.url} target="_blank" rel="noopener noreferrer">{tr("brain_device_open", lang)} ↗</a>
      <div class="device-code">
        <code>{challenge.userCode}</code>
        <button class="btn-ghost" type="button" onclick={copyUserCode}>{tr(copied ? "brain_device_copied" : "brain_device_copy", lang)}</button>
      </div>
      <div class="device-progress">
        <p class="login-progress"><span class="loading-pulse" aria-hidden="true"></span>{tr("brain_device_wait", lang)}</p>
        <button class="btn-ghost" type="button" onclick={() => cancelDevice()}>{tr("brain_login_cancel", lang)}</button>
      </div>
    </div>
  {:else if phase === "done"}
    <p class="notice notice-success login-error" role="status">{tr("brain_ok", lang)}</p>
  {/if}
</div>

<style>
  .brain-login { display: grid; gap: 0.55rem; }
  .login-start { width: 100%; padding-inline: 0.7rem; font-size: 0.64rem; }
  .login-error { margin: 0; font-size: 0.68rem; }
  .login-progress { display: flex; align-items: center; gap: 0.55rem; margin: 0; color: var(--color-muted); font-size: 0.68rem; }
  .login-steps { display: grid; gap: 0.5rem; }
  .device-code { display: flex; align-items: center; justify-content: space-between; gap: 0.55rem; border: 1px solid var(--color-border-strong); padding: 0.45rem; background: #000; }
  .device-code code { padding-inline: 0.35rem; color: var(--color-yellow); font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; letter-spacing: 0.08em; }
  .device-code :global(.btn-ghost) { min-height: 2rem; padding: 0.35rem 0.55rem; font-size: 0.58rem; }
  .device-progress { display: flex; align-items: center; justify-content: space-between; gap: 0.55rem; }
  .device-progress :global(.btn-ghost) { min-height: 2rem; flex: 0 0 auto; padding: 0.35rem 0.55rem; font-size: 0.58rem; }
</style>
