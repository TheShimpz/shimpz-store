<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  import { goto } from "$app/navigation";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import BrainLoginFlow from "$lib/components/BrainLoginFlow.svelte";
  import HudIcon from "$lib/components/HudIcon.svelte";
  import PageIntro from "$lib/components/PageIntro.svelte";
  import Seo from "$lib/components/Seo.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);

  const SEL_KEY = "shimpz_current_capsule";

  let phase = $state("checking"); // checking | login | none | ready
  let capsules = $state<any[]>([]);
  let selected = $state("");
  let brain = $state<any>(null); // {brain, title, configured, authenticated}
  let crew = $state<any[]>([]);
  let messages = $state<any[]>([]);
  let draft = $state("");
  let busy = $state(false);
  let status = $state(""); // the tool-status ticker while the brain works
  let uploading = $state(false);
  let thread = $state<HTMLElement | null>(null);
  let fileInput = $state<HTMLInputElement | null>(null);

  // markdown renderer — loaded client-side only (marked + DOMPurify), so SSR/prerender never touches
  // the browser build. Until it loads, replies render as safe escaped text.
  let renderMd = $state<(s: string) => string>((s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] as string));

  // The live bridge: one WebSocket per open capsule chat — the reply STREAMS in (text events), the
  // brain's mid-turn questions (shimpz-ask) arrive as pushes, tool activity ticks a status line.
  let ws = $state<WebSocket | null>(null);
  let wsReady = $state(false);

  async function refreshBrainStatus() {
    const cid = selected;
    if (!cid) return;
    const current = await fetch(`/api/capsules/${cid}/brain`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    if (current && selected === cid) brain = current;
  }

  function liveBrainMsg() {
    // the brain bubble currently being streamed into (create one if the last isn't it)
    let last = messages[messages.length - 1];
    if (!last || last.role !== "brain" || !last.streaming) {
      last = { role: "brain", text: "", streaming: true };
      messages.push(last);
    }
    return last;
  }

  function finishStreamingBrainMessage() {
    // A pushed question can sit after the live reply, so find the bubble instead of assuming it is last.
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message?.role === "brain" && message.streaming) {
        message.streaming = false;
        return;
      }
    }
  }

  function chatErrorText(statusCode: unknown, detailValue: unknown) {
    const detail = typeof detailValue === "string" ? detailValue.trim() : "";
    const normalized = detail.toLowerCase();
    if (Number(statusCode) === 409) {
      if (normalized.includes("active chat turn") || normalized.includes("already has an active")) {
        return tr("chat_turn_active", lang);
      }
      if (normalized.includes("not authenticated") || normalized.includes("configure the brain")) {
        return tr("brain_wait", lang);
      }
    }
    return "✗ " + (detail || "error");
  }

  function connectWs(cid = selected) {
    const previous = ws;
    ws = null;
    previous?.close();
    wsReady = false;
    if (!cid || selected !== cid) return;
    const proto = location.protocol === "https:" ? "wss://" : "ws://";
    const sock = new WebSocket(`${proto}${location.host}/api/capsules/${cid}/ws`);
    sock.onopen = () => {
      if (ws === sock && selected === cid) wsReady = true;
    };
    sock.onclose = () => {
      if (ws !== sock || selected !== cid) return;
      wsReady = false;
      ws = null;
      if (busy) {
        finishStreamingBrainMessage();
        busy = false;
        status = "";
        messages.push({ role: "system", tone: "error", text: tr("chat_disconnected", lang) });
        scrollDown(true);
      }
    };
    sock.onmessage = (ev) => {
      if (ws !== sock || selected !== cid) return;
      let m: any = {};
      try {
        m = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (m.type === "text") {
        // the growing answer — each event is the full text so far (mirrors the Telegram relay)
        liveBrainMsg().text = m.text || "";
      } else if (m.type === "tool") {
        status = "▸ " + (m.label || "");
      } else if (m.type === "done") {
        const b = liveBrainMsg();
        b.text = m.reply || b.text || "…";
        b.streaming = false;
        busy = false;
        status = "";
        void refreshBrainStatus();
      } else if (m.type === "stopped") {
        finishStreamingBrainMessage();
        busy = false;
        status = "";
      } else if (m.type === "error") {
        finishStreamingBrainMessage();
        busy = false;
        status = "";
        messages.push({ role: "system", tone: "error", text: chatErrorText(m.status, m.detail ?? m.error) });
      } else if (m.type === "ask") {
        messages.push({ role: "ask", rid: m.rid, text: m.text, options: m.options ?? [], answered: false, custom: "" });
      } else if (m.type === "answered" && m.answered) {
        const card = messages.find((x) => x.role === "ask" && x.rid === m.rid);
        if (card) card.answered = true;
      }
      // a fresh discrete message (a question, an error) may scroll smooth; a streaming delta must not
      scrollDown(m.type === "ask" || m.type === "error");
    };
    ws = sock;
  }

  function stopTurn() {
    if (wsReady && ws) ws.send(JSON.stringify({ type: "stop" }));
  }

  function answerAsk(card: any, answer: string) {
    if (!answer.trim() || card.answered || !wsReady) return;
    ws?.send(JSON.stringify({ type: "answer", rid: card.rid, answer: answer.trim() }));
    messages.push({ role: "captain", text: answer.trim() });
    stick = true;
    scrollDown(true);
  }

  let configureBusy = $state(false);
  let configureErr = $state("");
  let accountBrainsAvailable = $state(false);
  let brainChoice = $state("claude-code");
  let brainModel = $state("claude-sonnet-5");
  let loadedBrainChoice = $state("claude-code");
  let loadedBrainModel = $state("claude-sonnet-5");
  let brainSwapBusy = $state(false);
  let brainSwapErr = $state("");
  let brainSwapOk = $state("");

  const brainHasChanges = $derived(
    brainChoice !== loadedBrainChoice || brainModel.trim() !== loadedBrainModel,
  );
  const runtimeBusy = $derived(busy || brainSwapBusy);

  function defaultBrainModel(provider: string) {
    return provider === "claude-code" ? "claude-sonnet-5" : "";
  }

  function chooseBrain(event: Event) {
    brainChoice = (event.currentTarget as HTMLSelectElement).value;
    brainModel = defaultBrainModel(brainChoice);
    brainSwapErr = "";
    brainSwapOk = "";
  }

  async function applyAccountBrain() {
    if (!selected || configureBusy || brainSwapBusy) return;
    configureBusy = true;
    configureErr = "";
    try {
      const r = await fetch(`/api/capsules/${selected}/brain/configure`, { method: "POST" }).catch(() => null);
      const d = await r?.json().catch(() => ({}));
      if (!r?.ok) {
        configureErr = d?.detail ?? d?.error ?? tr("brain_apply_failed", lang);
        return;
      }
      await loadCapsuleContext();
      if (!brain?.configured) configureErr = tr("brain_apply_failed", lang);
    } finally {
      configureBusy = false;
    }
  }

  // Auto-follow the stream ONLY when the Captain is already at the bottom — never yank them back up
  // while they're reading history. During a stream we scroll with behavior:auto (smooth would restart
  // its animation every token and jank); discrete new messages may scroll smooth.
  let stick = $state(true);
  const escapeHtml = (s: string) => (s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] as string);

  function onThreadScroll() {
    if (!thread) return;
    stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 80;
  }

  async function scrollDown(smooth = false) {
    await tick();
    if (!thread || !stick) return;
    const rm = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    thread.scrollTo({ top: thread.scrollHeight, behavior: smooth && !rm ? "smooth" : "auto" });
  }

  async function loadCapsuleContext() {
    const cid = selected;
    brain = null;
    crew = [];
    if (!cid) return;
    localStorage.setItem(SEL_KEY, cid);
    const name = capsules.find((c) => c.id === cid)?.name ?? cid;
    localStorage.setItem(SEL_KEY + "_name", name);
    const [b, a] = await Promise.all([
      fetch(`/api/capsules/${cid}/brain`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch(`/api/capsules/${cid}/apps`).then((r) => (r.ok ? r.json() : { apps: [] })).catch(() => ({ apps: [] })),
    ]);
    if (selected !== cid) return;
    brain = b;
    crew = a.apps ?? [];
    const capsule = capsules.find((item) => item.id === cid);
    loadedBrainChoice = b?.brain ?? capsule?.brain ?? "claude-code";
    loadedBrainModel = String(b?.model ?? capsule?.model ?? defaultBrainModel(loadedBrainChoice));
    brainChoice = loadedBrainChoice;
    brainModel = loadedBrainModel;
    connectWs(cid);
  }

  function resetCapsuleSession() {
    configureErr = "";
    brainSwapErr = "";
    brainSwapOk = "";
    const previous = ws;
    ws = null;
    previous?.close();
    wsReady = false;
    busy = false;
    status = "";
    messages = [];
    draft = "";
  }

  async function changeCapsule(next: string, updateUrl = true) {
    if (brainSwapBusy || !capsules.some((capsule) => capsule.id === next) || next === selected) return;
    resetCapsuleSession();
    selected = next;
    if (updateUrl) {
      await goto(u.chat(lang, next), { keepFocus: true, noScroll: true });
    }
    await loadCapsuleContext();
  }

  async function swapBrain() {
    if (!selected || !brainHasChanges || brainSwapBusy || busy) return;
    const cid = selected;
    const capsule = capsules.find((item) => item.id === cid);
    if (!capsule) return;
    const capsuleName = String(capsule.name ?? "").trim();
    if (!capsuleName) {
      brainSwapErr = tr("brain_switch_failed", lang);
      return;
    }
    const targetBrain = brainChoice;
    const targetModel = brainModel.trim();
    brainSwapBusy = true;
    brainSwapErr = "";
    brainSwapOk = "";
    const payload: Record<string, string> = {
      name: capsuleName,
      brain: targetBrain,
      model: targetModel,
    };
    try {
      const response = await fetch("/api/capsules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        brainSwapErr = result?.detail ?? result?.error ?? tr("brain_switch_failed", lang);
        return;
      }
      if (selected !== cid) return;
      resetCapsuleSession();
      capsules = capsules.map((item) =>
        item.id === cid ? { ...item, brain: targetBrain, model: targetModel } : item,
      );
      await loadCapsuleContext();
      brainSwapOk = tr("brain_switch_ok", lang);
    } catch {
      brainSwapErr = tr("brain_switch_failed", lang);
    } finally {
      brainSwapBusy = false;
      syncCapsuleFromUrl();
    }
  }

  function syncCapsuleFromUrl() {
    if (phase !== "ready" || location.pathname !== u.chat(lang)) return;
    const requested = new URL(location.href).searchParams.get("capsule") ?? "";
    const next = capsules.some((capsule) => capsule.id === requested) ? requested : capsules[0]?.id ?? "";
    if (!next) return;
    if (requested !== next) history.replaceState(history.state, "", u.chat(lang, next));
    if (next !== selected) void changeCapsule(next, false);
  }

  async function boot() {
    const me = await (await fetch("/api/me")).json().catch(() => ({}));
    if (!me.authenticated) {
      phase = "login";
      return;
    }
    const [r, brainsResponse] = await Promise.all([
      fetch("/api/capsules"),
      fetch("/api/brains").catch(() => null),
    ]);
    const brainsResult = await brainsResponse?.json().catch(() => null);
    accountBrainsAvailable = Boolean(brainsResponse?.ok && Array.isArray(brainsResult?.brains));
    capsules = r.ok ? ((await r.json()).capsules ?? []) : [];
    if (capsules.length === 0) {
      phase = "none";
      return;
    }
    const requested = new URL(location.href).searchParams.get("capsule") ?? "";
    const stored = localStorage.getItem(SEL_KEY) ?? "";
    selected = capsules.some((c) => c.id === requested)
      ? requested
      : capsules.some((c) => c.id === stored)
        ? stored
        : capsules[0].id;
    if (requested !== selected) history.replaceState(history.state, "", u.chat(lang, selected));
    await loadCapsuleContext();
    phase = "ready";
  }

  async function send() {
    const text = draft.trim();
    if (!text || runtimeBusy || !selected || !brain?.configured) return;
    draft = "";
    busy = true;
    status = tr("chat_thinking", lang);
    messages.push({ role: "captain", text });
    stick = true; // sending re-engages auto-follow
    scrollDown(true);
    if (wsReady && ws) {
      ws.send(JSON.stringify({ type: "chat", message: text })); // reply STREAMS back as pushes
      return;
    }
    // fallback: socket down → the non-streaming POST
    try {
      const r = await fetch(`/api/capsules/${selected}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        messages.push({ role: "brain", text: d.reply || "…" });
        await refreshBrainStatus();
      } else {
        messages.push({ role: "system", tone: "error", text: chatErrorText(r.status, d.detail ?? d.error) });
      }
    } catch {
      messages.push({ role: "system", tone: "error", text: "✗ network error" });
    } finally {
      busy = false;
      status = "";
      scrollDown(true);
    }
  }

  async function upload(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file || !selected || uploading || brainSwapBusy || !brain?.configured) return;
    uploading = true;
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await fetch(`/api/capsules/${selected}/files`, { method: "POST", body: form });
      const d = await r.json().catch(() => ({}));
      messages.push(
        r.ok
          ? { role: "system", tone: "success", text: `${tr("chat_file_ok", lang)} ${d.path}` }
          : { role: "system", tone: "error", text: "✗ " + (d.error ?? d.detail ?? "upload error") },
      );
    } finally {
      uploading = false;
      if (fileInput) fileInput.value = "";
      stick = true;
      scrollDown(true);
    }
  }

  onMount(async () => {
    // markdown, browser-only: raw brain output is escaped first (marked won't emit HTML from us),
    // then DOMPurify strips anything unsafe — so a reply that contains HTML/script can't run.
    try {
      const [{ marked }, dp] = await Promise.all([import("marked"), import("dompurify")]);
      const purify = dp.default;
      renderMd = (s: string) => purify.sanitize(marked.parse(s ?? "", { breaks: true, gfm: true, async: false }) as string);
    } catch {
      /* keep the escaped-text fallback */
    }
    boot();
  });
  onDestroy(() => ws?.close());
</script>

<svelte:window onpopstate={syncCapsuleFromUrl} />

<Seo title={tr("chat_title", lang)} description={tr("chat_lead", lang)} {lang} />

<section class="wrap chat-page">
  {#snippet chatMedia()}
    <div class="chat-hero-icon"><HudIcon name="chat" size={40} /></div>
  {/snippet}

  {#snippet chatMeta()}
    {#if phase === "ready"}
      <span class="connection-chip" class:online={wsReady}>
        <i aria-hidden="true"></i>
        {wsReady ? tr("chat_connection_live", lang) : tr("chat_connection_offline", lang)}
      </span>
      <span class="badge">{crew.length} {tr("chat_hosted_crew_count", lang)}</span>
    {/if}
  {/snippet}

  <PageIntro
    headingId="chat-title"
    kicker={tr("chat_kicker", lang)}
    title={capsules.find((capsule) => capsule.id === selected)?.name || tr("nav_chat", lang)}
    description={tr("chat_lead", lang)}
    media={chatMedia}
    meta={chatMeta}
  />

  {#if phase === "checking"}
    <div class="panel page-state" aria-live="polite"><span class="loading-pulse" aria-hidden="true"></span><p>{tr("loading", lang)}</p></div>
  {:else if phase === "login"}
    <div class="panel page-state"><HudIcon name="user" size={28} /><p>{tr("chat_login", lang)}</p><a class="btn-primary" href={u.login(lang)}>{tr("log_in", lang)}</a></div>
  {:else if phase === "none"}
    <div class="panel page-state"><HudIcon name="capsule" size={30} /><p>{tr("chat_no_capsule", lang)}</p><a class="btn-primary" href={u.capsule(lang)}>{tr("capsule_submit", lang)}</a></div>
  {:else}
    <div class="chat-workspace">
      <aside class="control-rail" aria-label={tr("chat_capsule_title", lang)}>
        <section class="panel control-card" aria-labelledby="capsule-context-title">
          <header class="control-heading">
            <span class="control-icon" aria-hidden="true"><HudIcon name="capsule" size={21} /></span>
            <div><p class="kicker">Capsule</p><h2 id="capsule-context-title">{tr("chat_capsule_title", lang)}</h2></div>
          </header>
          <p class="control-help">{tr("chat_capsule_help", lang)}</p>
          <label class="field-stack">
            <span>{tr("my_capsules", lang)}</span>
            <select
              class="field field-sm"
              aria-label={tr("my_capsules", lang)}
              value={selected}
              disabled={runtimeBusy}
              onchange={(event) => changeCapsule((event.currentTarget as HTMLSelectElement).value)}>
              {#each capsules as c (c.id)}<option value={c.id}>{c.name || c.id}</option>{/each}
            </select>
          </label>
          <code class="capsule-id">{selected}</code>
        </section>

        <section class="panel control-card brain-control" aria-labelledby="brain-control-title" aria-busy={brainSwapBusy}>
          <header class="control-heading">
            <span class="control-icon brain-icon" aria-hidden="true"><HudIcon name="brain" size={21} /></span>
            <div><p class="kicker">Runtime</p><h2 id="brain-control-title">{tr("chat_brain_title", lang)}</h2></div>
            {#if brain}
              <span class="brain-state" class:ready={brain.authenticated} class:pending={brain.configured && !brain.authenticated}>
                <i aria-hidden="true"></i>
                {brain.authenticated ? tr("brain_authenticated_verified", lang) : brain.configured ? tr("brain_verification_pending", lang) : tr("brain_not_configured", lang)}
              </span>
            {/if}
          </header>
          <p class="control-help">{tr("chat_brain_help", lang)}</p>

          {#if brain}
            <div class="brain-editor">
              <label class="field-stack">
                <span>{tr("brain_provider", lang)}</span>
                <select class="field field-sm" value={brainChoice} disabled={runtimeBusy || configureBusy} onchange={chooseBrain}>
                  <option value="claude-code">Claude Code</option>
                  <option value="codex">Codex</option>
                </select>
              </label>
              <label class="field-stack">
                <span>{tr("model_label", lang)}</span>
                <input class="field field-sm" bind:value={brainModel} maxlength="128" autocomplete="off" disabled={runtimeBusy || configureBusy} placeholder={tr("model_default", lang)} />
              </label>
              <button class="btn-primary brain-switch" type="button" disabled={!brainHasChanges || runtimeBusy || configureBusy} onclick={swapBrain}>
                <HudIcon name="retry" size={16} />
                {brainSwapBusy ? tr("brain_switching", lang) : tr("brain_switch", lang)}
              </button>
              <p class="brain-hint"><HudIcon name="shield" size={15} />{tr("brain_switch_hint", lang)}</p>
              {#if brainSwapErr}<p class="notice notice-error compact-notice" role="alert">{brainSwapErr}</p>{/if}
              {#if brainSwapOk}<p class="notice notice-success compact-notice" role="status">{brainSwapOk}</p>{/if}
            </div>

            <div class="brain-access">
              <div class="access-heading"><HudIcon name="key" size={16} /><span>{tr("brain_auth_type", lang)}</span></div>
              {#if brain.configured}
                {#if brain.authenticated}
                  <p class="access-state success"><HudIcon name="check" size={16} />{tr("brain_authenticated_verified", lang)}</p>
                {:else}
                  <p class="notice compact-notice">{tr("brain_verification_pending", lang)}</p>
                {/if}
              {:else}
                <p class="access-copy">{tr("brain_wait", lang)}</p>
                <div class="access-actions">
                  <a class="btn-primary" href={u.account(lang)}>{tr("brain_account_cta", lang)}</a>
                  {#if accountBrainsAvailable}
                    <button class="btn-ghost" type="button" disabled={configureBusy || brainSwapBusy} onclick={applyAccountBrain}>
                      {configureBusy ? "…" : tr("brain_apply", lang)}
                    </button>
                  {/if}
                </div>
                {#if configureErr}<p class="notice notice-error compact-notice" role="alert">{configureErr}</p>{/if}

                {#if brain.brain === "claude-code" || brain.brain === "codex"}
                  <p class="oauth-divider">{tr("brain_interactive_or", lang)}</p>
                  <BrainLoginFlow {lang} capsuleId={selected} provider={brain.brain} oncomplete={loadCapsuleContext} />
                {/if}
              {/if}
            </div>
          {:else}
            <p class="oauth-progress"><span class="loading-pulse" aria-hidden="true"></span>{tr("loading", lang)}</p>
          {/if}
        </section>

        <section class="panel control-card" aria-labelledby="assistants-context-title">
          <header class="control-heading">
            <span class="control-icon assistant-icon" aria-hidden="true"><HudIcon name="assistants" size={21} /></span>
            <div><p class="kicker">Capsule</p><h2 id="assistants-context-title">{tr("crew_title", lang)}</h2></div>
            <span class="assistant-count">{crew.length}</span>
          </header>
          <p class="control-help">{tr("chat_assistants_help", lang)}</p>
          {#if crew.length}
            <ul class="crew-list">
              {#each crew as assistant (assistant.app)}
                <li><HudIcon name="assistants" size={16} /><span>{assistant.app}</span><small>{assistant.status}</small></li>
              {/each}
            </ul>
          {:else}
            <p class="empty-crew">{tr("crew_empty", lang)}</p>
          {/if}
          <div class="assistant-boundary">
            <p>{tr("chat_local_assistant_boundary", lang)}</p>
            <a href="http://127.0.0.1:7777/assistants/" target="_blank" rel="noopener noreferrer">
              {tr("chat_open_local_admin", lang)} <span aria-hidden="true">↗</span>
            </a>
          </div>
        </section>
      </aside>

      <main class="conversation-shell" aria-labelledby="conversation-title">
        <header class="conversation-header">
          <span class="conversation-avatar" aria-hidden="true"><HudIcon name="brain" size={24} /></span>
          <div>
            <p class="kicker">{tr("chat_brain_target", lang)}</p>
            <h2 id="conversation-title">{brain?.title || tr("brain_label", lang)}</h2>
          </div>
          <span class="conversation-status" class:online={wsReady && brain?.configured}>
            <i aria-hidden="true"></i>{brain?.configured ? tr("chat_ready", lang) : tr("chat_setup_required", lang)}
          </span>
        </header>
        <div
          bind:this={thread}
          onscroll={onThreadScroll}
          role="log"
          aria-live="polite"
          aria-relevant="additions"
          aria-label={tr("chat_thread_label", lang)}
          aria-busy={runtimeBusy}
          tabindex="-1"
          class="conversation-thread">
          {#each messages as m, i (i)}
            {#if m.role === "captain"}
              <div class="message captain-message">{m.text}</div>
            {:else if m.role === "brain"}
              <div class="md message brain-message" class:caret={m.streaming} class:whitespace-pre-wrap={m.streaming}>{@html m.streaming ? escapeHtml(m.text) : renderMd(m.text || "")}</div>
            {:else if m.role === "ask"}
              <div class="message ask-message" class:opacity-60={m.answered}>
                <p class="whitespace-pre-wrap"><span style="color:var(--color-primary)">?</span> {m.text}</p>
                {#if !m.answered}
                  <div class="flex flex-wrap gap-2">
                    {#each m.options as opt, oi (oi)}
                      <button class="btn-ghost min-h-11 !px-3 !py-1.5 text-xs" onclick={() => answerAsk(m, opt)}>
                        {#if oi === 0}
                          <svg class="size-3.5 shrink-0" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="miter">
                            <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z" />
                          </svg>
                        {/if}
                        {opt}
                      </button>
                    {/each}
                  </div>
                  <div class="flex gap-2">
                    <input class="field field-sm min-h-11 min-w-0 flex-1 !text-xs" placeholder={tr("ask_custom", lang)} bind:value={m.custom} onkeydown={(event) => event.key === "Enter" && !event.isComposing && answerAsk(m, m.custom)} />
                    <button class="btn-ghost min-h-11 !px-3 !py-1.5 text-xs" disabled={!m.custom?.trim()} onclick={() => answerAsk(m, m.custom)}>{tr("chat_send", lang)}</button>
                  </div>
                {:else}
                  <p class="text-xs dim">{tr("ask_answered", lang)}</p>
                {/if}
              </div>
            {:else}
              <p
                class="px-3 py-2 text-center text-xs"
                class:dim={!m.tone}
                class:notice={Boolean(m.tone)}
                class:notice-error={m.tone === "error"}
                class:notice-success={m.tone === "success"}
                role={m.tone === "error" ? "alert" : m.tone === "success" ? "status" : undefined}
              >{m.text}</p>
            {/if}
          {/each}
          {#if busy && status}<p class="turn-status"><span class="loading-pulse" aria-hidden="true"></span>{status}</p>{/if}
          {#if messages.length === 0 && !busy}<div class="conversation-empty"><HudIcon name="chat" size={30} /><p>{tr("chat_empty", lang)}</p></div>{/if}
        </div>
        <div class="composer">
          <input bind:this={fileInput} type="file" class="hidden" onchange={upload} />
          <button class="btn-ghost composer-icon" type="button" title={tr("chat_attach", lang)} aria-label={tr("chat_attach", lang)} disabled={uploading || runtimeBusy || !brain?.configured} onclick={() => fileInput?.click()}>
            {#if uploading}
              …
            {:else}
              <HudIcon name="attach" size={18} />
            {/if}
          </button>
          <textarea
            class="field field-area composer-input"
            placeholder={tr("chat_placeholder", lang)}
            aria-label={tr("chat_placeholder", lang)}
            rows="2"
            disabled={runtimeBusy || !brain?.configured}
            bind:value={draft}
            onkeydown={(event) => event.key === "Enter" && !event.shiftKey && !event.isComposing && (event.preventDefault(), send())}></textarea>
          {#if busy}
            <button class="btn-danger composer-action" type="button" onclick={stopTurn}><HudIcon name="stop" size={17} />{tr("chat_stop", lang)}</button>
          {:else}
            <button class="btn-primary composer-action" type="button" disabled={!draft.trim() || runtimeBusy || !brain?.configured} onclick={send}><HudIcon name="send" size={17} />{tr("chat_send", lang)}</button>
          {/if}
        </div>
      </main>
    </div>
  {/if}
</section>

<style>
  .chat-page { padding-block: 2.5rem 4rem; }

  .chat-hero-icon {
    display: grid;
    width: 4.5rem;
    height: 4.5rem;
    place-items: center;
    color: var(--color-cyan);
    background: color-mix(in oklab, var(--color-cyan) 7%, #000);
    box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-cyan) 46%, var(--color-border));
    clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
  }

  .connection-chip,
  .conversation-status,
  .brain-state {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: var(--color-muted);
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .connection-chip i,
  .conversation-status i,
  .brain-state i {
    width: 0.45rem;
    height: 0.45rem;
    flex: none;
    background: var(--color-muted-2);
    box-shadow: 0 0 0 1px #000;
  }

  .connection-chip.online,
  .conversation-status.online,
  .brain-state.ready { color: var(--color-green); }

  .connection-chip.online i,
  .conversation-status.online i,
  .brain-state.ready i {
    background: var(--color-green);
    box-shadow: 0 0 8px color-mix(in oklab, var(--color-green) 64%, transparent);
  }

  .brain-state.pending { color: var(--color-yellow); }
  .brain-state.pending i { background: var(--color-yellow); }

  .page-state {
    display: flex;
    min-height: 14rem;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-top: 1.5rem;
    color: var(--color-muted);
    text-align: center;
  }

  .page-state > :global(svg) { color: var(--color-cyan); }
  .page-state p { max-width: 34rem; }

  .loading-pulse {
    width: 0.55rem;
    height: 0.55rem;
    flex: none;
    background: var(--color-cyan);
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.7);
    animation: pulse 1.2s steps(2, end) infinite;
  }

  .chat-workspace {
    display: grid;
    grid-template-columns: minmax(17.5rem, 20rem) minmax(0, 1fr);
    align-items: start;
    gap: 1rem;
    margin-top: 1.5rem;
  }

  .control-rail {
    position: sticky;
    top: 7rem;
    display: grid;
    max-height: calc(100vh - 8rem);
    gap: 0.8rem;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--color-border-strong) transparent;
  }

  .control-card { padding: 1rem; }
  .control-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 2px;
    background: color-mix(in oklab, var(--color-cyan) 48%, transparent);
  }

  .control-heading {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.7rem;
  }

  .control-icon,
  .conversation-avatar {
    display: grid;
    width: 2.5rem;
    height: 2.5rem;
    flex: none;
    place-items: center;
    color: var(--color-cyan);
    background: #000;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(7px 0, 100% 0, 100% calc(100% - 7px), calc(100% - 7px) 100%, 0 100%, 0 7px);
  }

  .brain-icon { color: var(--color-magenta); }
  .assistant-icon { color: var(--color-yellow); }

  .control-heading .kicker,
  .conversation-header .kicker { margin: 0 0 0.08rem; font-size: 0.55rem; }

  .control-heading h2,
  .conversation-header h2 {
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.2;
    letter-spacing: -0.025em;
  }

  .control-help {
    margin: 0.85rem 0;
    color: var(--color-muted);
    font-size: 0.74rem;
    line-height: 1.55;
  }

  .field-stack { display: grid; gap: 0.35rem; }
  .field-stack > span,
  .access-heading {
    color: var(--color-muted);
    font-family: var(--font-mono);
    font-size: 0.61rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .capsule-id {
    display: block;
    max-width: 100%;
    margin-top: 0.65rem;
    overflow: hidden;
    color: var(--color-muted-2);
    font-size: 0.58rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .brain-state { justify-self: end; font-size: 0.54rem; text-align: right; }
  .brain-editor,
  .brain-access { display: grid; gap: 0.65rem; }
  .brain-editor { padding-top: 0.1rem; }
  .brain-access { margin-top: 0.9rem; border-top: 1px solid var(--color-border); padding-top: 0.85rem; }
  .brain-switch { width: 100%; min-height: 2.55rem; padding: 0.55rem 0.8rem; font-size: 0.68rem; }

  .brain-hint,
  .access-copy,
  .oauth-progress,
  .empty-crew {
    margin: 0;
    color: var(--color-muted);
    font-size: 0.7rem;
    line-height: 1.5;
  }

  .brain-hint,
  .oauth-progress,
  .access-heading,
  .access-state { display: flex; align-items: flex-start; gap: 0.45rem; }
  .brain-hint { color: var(--color-muted-2); }
  .brain-hint > :global(svg) { margin-top: 0.12rem; color: var(--color-cyan); }
  .compact-notice { margin: 0; padding: 0.65rem 0.75rem; font-size: 0.68rem; line-height: 1.45; }
  .access-heading { align-items: center; color: var(--color-fg); }
  .access-heading > :global(svg) { color: var(--color-cyan); }
  .access-state { margin: 0; color: var(--color-muted); font-size: 0.72rem; }
  .access-state.success { color: var(--color-green); }
  .access-actions { display: grid; gap: 0.5rem; }
  .access-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .access-actions > :global(*) { min-width: 0; padding-inline: 0.65rem; font-size: 0.62rem; }
  .oauth-divider { margin: 0.1rem 0; color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.59rem; text-align: center; text-transform: uppercase; }
  .oauth-progress { align-items: center; }

  .assistant-count {
    min-width: 1.8rem;
    padding: 0.15rem 0.4rem;
    color: var(--color-yellow);
    background: color-mix(in oklab, var(--color-yellow) 7%, #000);
    box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-yellow) 35%, var(--color-border));
    font-family: var(--font-mono);
    font-size: 0.64rem;
    text-align: center;
  }

  .crew-list { display: grid; margin: 0; padding: 0; list-style: none; }
  .crew-list li {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.45rem;
    border-top: 1px solid var(--color-border);
    padding: 0.55rem 0;
    color: var(--color-fg);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }
  .crew-list li > :global(svg) { color: var(--color-yellow); }
  .crew-list small { color: var(--color-muted-2); font-size: 0.56rem; text-transform: uppercase; }
  .assistant-boundary { margin-top: 0.75rem; border-top: 1px solid var(--color-border); padding-top: 0.7rem; }
  .assistant-boundary p { margin: 0; color: var(--color-muted); font-size: 0.68rem; line-height: 1.45; }
  .assistant-boundary a { display: inline-block; margin-top: 0.45rem; color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.62rem; font-weight: 600; text-decoration: underline; text-decoration-style: dashed; text-underline-offset: 0.22em; }

  .conversation-shell {
    display: flex;
    min-width: 0;
    min-height: 42rem;
    flex-direction: column;
    overflow: hidden;
    background: linear-gradient(180deg, var(--color-card-2), #020202);
    box-shadow: inset 0 0 0 1px var(--color-border);
    clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
  }

  .conversation-header {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.75rem;
    border-bottom: 1px solid var(--color-border);
    padding: 0.9rem 1rem;
    background: #050505;
  }

  .conversation-avatar { width: 2.75rem; height: 2.75rem; color: var(--color-magenta); }
  .conversation-status { justify-self: end; }

  .conversation-thread {
    display: flex;
    height: clamp(31rem, 62vh, 48rem);
    min-height: 28rem;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 0.85rem;
    overflow-y: auto;
    padding: 1.2rem;
    background-image:
      linear-gradient(rgba(0, 240, 255, 0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 240, 255, 0.018) 1px, transparent 1px);
    background-size: 32px 32px;
    scrollbar-width: thin;
    scrollbar-color: var(--color-border-strong) transparent;
    outline: none;
  }

  .message {
    width: fit-content;
    max-width: min(86%, 46rem);
    padding: 0.8rem 0.95rem;
    font-size: 0.86rem;
    line-height: 1.58;
    overflow-wrap: anywhere;
  }

  .captain-message {
    align-self: flex-end;
    color: #dffcff;
    background: color-mix(in oklab, var(--color-cyan) 11%, #050505);
    box-shadow: inset 2px 0 0 var(--color-cyan), inset 0 0 0 1px color-mix(in oklab, var(--color-cyan) 26%, var(--color-border));
    clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  }

  .brain-message,
  .ask-message {
    align-self: flex-start;
    background: var(--color-elevated);
    box-shadow: inset 2px 0 0 var(--color-magenta), inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(8px 0, 100% 0, 100% 100%, 8px 100%, 0 calc(100% - 8px), 0 8px);
  }

  .ask-message { display: grid; gap: 0.7rem; border-left-color: var(--color-yellow); box-shadow: inset 2px 0 0 var(--color-yellow), inset 0 0 0 1px var(--color-border-strong); }
  .ask-message p { margin: 0; }

  .conversation-empty {
    display: grid;
    max-width: 25rem;
    place-items: center;
    gap: 0.75rem;
    margin: auto;
    color: var(--color-muted);
    text-align: center;
  }
  .conversation-empty > :global(svg) { color: var(--color-cyan); opacity: 0.7; }
  .conversation-empty p { margin: 0; }

  .turn-status {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: 0;
    color: var(--color-cyan);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .composer {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: end;
    gap: 0.65rem;
    border-top: 1px solid var(--color-border);
    padding: 0.85rem;
    background: #050505;
  }

  .composer-input { max-height: 12rem; min-height: 3rem; resize: vertical; line-height: 1.45; }
  .composer-icon { width: 2.9rem; min-height: 3rem; padding: 0; }
  .composer-action { min-height: 3rem; padding-inline: 1rem; font-size: 0.7rem; }

  @keyframes pulse { 50% { opacity: 0.35; } }

  @media (max-width: 1050px) {
    .chat-workspace { grid-template-columns: 1fr; }
    .control-rail { position: static; grid-template-columns: repeat(2, minmax(0, 1fr)); max-height: none; overflow: visible; }
    .brain-control { grid-row: span 2; }
  }

  @media (max-width: 720px) {
    .control-rail { grid-template-columns: 1fr; }
    .brain-control { grid-row: auto; }
    .conversation-header { grid-template-columns: auto minmax(0, 1fr); }
    .conversation-status { grid-column: 2; justify-self: start; }
    .message { max-width: 94%; }
  }

  @media (max-width: 520px) {
    .chat-page { padding-top: 1.5rem; }
    .page-state { flex-direction: column; }
    .control-heading { grid-template-columns: auto minmax(0, 1fr); }
    .brain-state { grid-column: 2; justify-self: start; text-align: left; }
    .access-actions { grid-template-columns: 1fr; }
    .conversation-thread { height: min(58vh, 36rem); min-height: 24rem; padding: 0.8rem; }
    .composer { grid-template-columns: minmax(0, 1fr) auto; }
    .composer-input { grid-column: 1 / -1; grid-row: 1; }
    .composer-icon { grid-column: 1; justify-self: start; }
    .composer-action { grid-column: 2; }
  }

  @media (forced-colors: active) {
    .chat-hero-icon,
    .control-icon,
    .conversation-avatar,
    .conversation-shell,
    .control-card,
    .message { border: 1px solid CanvasText; }
    .loading-pulse,
    .connection-chip i,
    .conversation-status i,
    .brain-state i { background: CanvasText; }
  }
</style>
