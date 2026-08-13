<script lang="ts">
  import { onMount } from "svelte";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { parseAssistantCatalog } from "$lib/assistantCatalog.js";
  import {
    ASSISTANT_INSTALL_ACK_TIMEOUT_MS,
    acceptAssistantStoreContext,
    acceptAssistantStoreState,
    assistantStoreActionForState,
    classifyAssistantInstallAck,
    classifyAssistantUninstallAck,
    createAssistantStoreFrameMessage,
    createAssistantInstallRequest,
    createAssistantUninstallRequest,
    shouldReconcileAssistantStoreAction,
  } from "$lib/assistantInstallBridge.js";
  import { closedAssistantStoreHref } from "$lib/cloudAssistantLifecycle.js";
  import { AssistantIcon, PageIntro } from "@shimpz/frontend";
  import HudIcon from "$lib/components/HudIcon.svelte";

  type ActionKind = "install" | "uninstall";
  type ActionState = "idle" | "pending" | "sent" | "error";
  type ContextState = "connecting" | "ready" | "error";
  type InventoryState = "loading" | "ready" | "error";
  type CatalogAssistant = ReturnType<typeof parseAssistantCatalog>[number];
  type PendingAction = {
    action: ActionKind;
    parentOrigin: string;
    timeout: ReturnType<typeof setTimeout>;
  };

  let {
    lang,
    embedded = false,
    assistants = [],
    catalogState: providedCatalogState = "ready",
    onRetry = () => {},
  }: {
    lang: Locale;
    embedded?: boolean;
    assistants?: readonly CatalogAssistant[];
    catalogState?: "loading" | "ready" | "error";
    onRetry?: () => void;
  } = $props();
  let actionStates = $state<Record<string, ActionState>>({});
  let actionKinds = $state<Record<string, ActionKind>>({});
  let contextState = $state<ContextState>("connecting");
  let inventoryState = $state<InventoryState>("loading");
  let installedAssistantIds = $state<string[]>([]);
  let parentOrigin = $state("");
  let storeElement = $state<HTMLElement>();
  const pendingActions = new Map<string, PendingAction>();
  let contextTimeout: ReturnType<typeof setTimeout> | undefined;
  let frameRequest = 0;
  let embeddedAssistants = $state<readonly CatalogAssistant[]>([]);
  let embeddedCatalogState = $state<"loading" | "ready" | "error">("loading");
  const assistantCatalog = $derived(embedded ? embeddedAssistants : assistants);
  const catalogState = $derived(embedded ? embeddedCatalogState : providedCatalogState);

  function actionState(assistant: string): ActionState {
    return actionStates[assistant] ?? "idle";
  }

  function setActionState(assistant: string, action: ActionKind, state: ActionState) {
    actionKinds = { ...actionKinds, [assistant]: action };
    actionStates = { ...actionStates, [assistant]: state };
  }

  function finishActionRequest(assistant: string, state: "sent" | "error") {
    const pending = pendingActions.get(assistant);
    if (pending) clearTimeout(pending.timeout);
    pendingActions.delete(assistant);
    if (pending) setActionState(assistant, pending.action, state);
  }

  function localAssistantInstalled(assistant: string): boolean {
    return assistantStoreActionForState(inventoryState, installedAssistantIds, assistant) === "uninstall";
  }

  function renderedAssistantInstalled(assistant: string): boolean {
    return embedded && localAssistantInstalled(assistant);
  }

  function inventoryBlocksAction(assistant: string): boolean {
    return assistantStoreActionForState(inventoryState, installedAssistantIds, assistant) === "blocked";
  }

  function requestAssistantAction(assistant: CatalogAssistant) {
    const assistantId = assistant.id;
    if (pendingActions.has(assistantId)) return;
    const resolvedAction = assistantStoreActionForState(inventoryState, installedAssistantIds, assistantId);
    if (resolvedAction === "blocked") return;
    const action: ActionKind = resolvedAction;
    try {
      if (window.parent === window) throw new Error("not embedded");
      if (!parentOrigin) throw new Error("local Admin context unavailable");
      const request = action === "uninstall"
        ? createAssistantUninstallRequest(assistantId)
        : createAssistantInstallRequest(assistantId, assistant.sourceDigest);
      setActionState(assistantId, action, "pending");
      window.parent.postMessage(request, parentOrigin);
      const timeout = setTimeout(
        () => finishActionRequest(assistantId, "error"),
        ASSISTANT_INSTALL_ACK_TIMEOUT_MS,
      );
      pendingActions.set(assistantId, { action, parentOrigin, timeout });
    } catch {
      setActionState(assistantId, action, "error");
    }
  }

  function reconcileAuthoritativeState(installed: string[]) {
    const nextStates = { ...actionStates };
    const nextKinds = { ...actionKinds };
    for (const [assistant, action] of Object.entries(actionKinds)) {
      if (!shouldReconcileAssistantStoreAction(action, actionState(assistant), "ready", installed, assistant)) {
        continue;
      }
      const pending = pendingActions.get(assistant);
      if (pending) clearTimeout(pending.timeout);
      pendingActions.delete(assistant);
      delete nextStates[assistant];
      delete nextKinds[assistant];
    }
    actionStates = nextStates;
    actionKinds = nextKinds;
  }

  function actionLabel(assistant: string): string {
    if (actionState(assistant) === "pending") return tr("assistants_request_waiting", lang);
    if (contextState !== "ready") return tr("assistants_admin_connecting", lang);
    if (inventoryState === "loading") return tr("assistants_inventory_loading", lang);
    if (inventoryState === "error") return tr("assistants_inventory_unavailable", lang);
    return tr(localAssistantInstalled(assistant) ? "assistants_uninstall_local" : "assistants_install_local", lang);
  }

  function actionStatus(assistant: string): string {
    const uninstall = actionKinds[assistant] === "uninstall";
    const failed = actionState(assistant) === "error";
    if (uninstall) {
      return tr(failed ? "assistants_uninstall_request_failed" : "assistants_uninstall_request_sent", lang);
    }
    return tr(failed ? "assistants_request_failed" : "assistants_request_sent", lang);
  }

  async function loadAssistantCatalog() {
    embeddedCatalogState = "loading";
    try {
      const response = await fetch("/api/assistants", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      embeddedAssistants = parseAssistantCatalog(await response.json());
      embeddedCatalogState = "ready";
    } catch {
      embeddedAssistants = [];
      embeddedCatalogState = "error";
    }
  }

  function measureFrameHeight(): number {
    const contentBottom = storeElement
      ? storeElement.getBoundingClientRect().bottom + window.scrollY + 32
      : 0;
    return contentBottom;
  }

  function emitFrameMeasurement() {
    if (!embedded || window.parent === window) return;
    window.parent.postMessage(createAssistantStoreFrameMessage(measureFrameHeight()), "*");
  }

  function scheduleFrameMeasurement() {
    if (frameRequest) cancelAnimationFrame(frameRequest);
    frameRequest = requestAnimationFrame(() => {
      frameRequest = 0;
      emitFrameMeasurement();
    });
  }

  function requestAdminContext() {
    if (!embedded || window.parent === window) return;
    if (!parentOrigin) contextState = "connecting";
    emitFrameMeasurement();
    if (parentOrigin) return;
    if (contextTimeout) clearTimeout(contextTimeout);
    contextTimeout = setTimeout(() => {
      if (!parentOrigin) contextState = "error";
    }, ASSISTANT_INSTALL_ACK_TIMEOUT_MS);
  }

  function receiveStoreMessage(event: MessageEvent) {
    const contextOrigin = acceptAssistantStoreContext(event, window.parent);
    if (contextOrigin) {
      parentOrigin = contextOrigin;
      contextState = "ready";
      if (contextTimeout) clearTimeout(contextTimeout);
      contextTimeout = undefined;
      return;
    }

    const storeState = parentOrigin
      ? acceptAssistantStoreState(event, window.parent, parentOrigin)
      : null;
    if (storeState) {
      inventoryState = storeState.status;
      installedAssistantIds = storeState.installed;
      if (storeState.status === "ready") reconcileAuthoritativeState(storeState.installed);
      return;
    }

    const assistant =
      event.data && typeof event.data === "object" && typeof event.data.assistant === "string"
        ? event.data.assistant
        : "";
    const pending = pendingActions.get(assistant);
    if (!pending) return;
    const classifyAck = pending.action === "uninstall"
      ? classifyAssistantUninstallAck
      : classifyAssistantInstallAck;
    const result = classifyAck(event, {
      parentWindow: window.parent,
      parentOrigin: pending.parentOrigin,
      assistant,
    });
    if (result === "accepted") finishActionRequest(assistant, "sent");
    else if (result === "invalid") finishActionRequest(assistant, "error");
  }

  onMount(() => {
    if (!embedded) return;
    document.body.classList.add("assistant-store-embedded");
    void loadAssistantCatalog();
    window.addEventListener("message", receiveStoreMessage);
    let mounted = true;
    let resizeObserver: ResizeObserver | undefined;

    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(scheduleFrameMeasurement);
      if (storeElement) resizeObserver.observe(storeElement);
    }
    requestAdminContext();
    scheduleFrameMeasurement();
    void document.fonts?.ready.then(() => {
      if (mounted) scheduleFrameMeasurement();
    });
    return () => {
      mounted = false;
      document.body.classList.remove("assistant-store-embedded");
      window.removeEventListener("message", receiveStoreMessage);
      resizeObserver?.disconnect();
      if (frameRequest) cancelAnimationFrame(frameRequest);
      if (contextTimeout) clearTimeout(contextTimeout);
      for (const pending of pendingActions.values()) clearTimeout(pending.timeout);
      pendingActions.clear();
    };
  });
</script>

<section
  bind:this={storeElement}
  class:embedded
  class:wrap={!embedded}
  class="assistants-page"
  aria-label={embedded ? tr("assistants_title", lang) : undefined}
  aria-labelledby={embedded ? undefined : "assistants-title"}>
  {#if !embedded}
    <PageIntro
      titleId="assistants-title"
      kicker={tr("assistants_preview", lang)}
      title={tr("assistants_title", lang)}
      lead={tr("assistants_lead", lang)} />
  {/if}

  {#if embedded && contextState === "error"}
    <div class="context-error" role="alert">
      <span>{tr("assistants_admin_connection_failed", lang)}</span>
      <button type="button" onclick={requestAdminContext}>
        {tr("assistants_admin_connection_retry", lang)}
      </button>
    </div>
  {/if}

  {#if catalogState === "error"}
    <div class="context-error" role="alert">
      <span>{tr("assistants_catalog_unavailable", lang)}</span>
      <button type="button" onclick={embedded ? loadAssistantCatalog : onRetry}>
        {tr("assistants_catalog_retry", lang)}
      </button>
    </div>
  {/if}

  <div class="assistant-grid" aria-busy={catalogState === "loading"}>
    {#each assistantCatalog as assistant (assistant.id)}
      <article
        id={`assistant-${assistant.id}`}
        class:installed={renderedAssistantInstalled(assistant.id)}
        class="assistant-card">
        <div class="assistant-details">
          <div class="assistant-heading">
            <AssistantIcon
              size={64}
              src={`/api/assistant-icons/${assistant.sourceDigest.slice(7)}/${assistant.iconDigest.slice(7)}.png`}
            />
            <div class="assistant-identity">
              <h2>
                {#if embedded}
                  {assistant.name}
                {:else}
                  <a class="assistant-link" href={closedAssistantStoreHref(lang, assistant.id)}>{assistant.name}</a>
                {/if}
              </h2>
              <p>{assistant.creators.join(", ")}</p>
            </div>
            <span class="free-badge">{tr("assistants_free", lang)}</span>
          </div>
          <p class="assistant-summary">{assistant.summary}</p>
        </div>

        {#if embedded}
          <div class:persistent={actionState(assistant.id) !== "idle"} class="assistant-action">
            <button
              class:btn-primary={!localAssistantInstalled(assistant.id)}
              class:btn-danger={localAssistantInstalled(assistant.id)}
              class="install-action"
              type="button"
              disabled={contextState !== "ready" || inventoryBlocksAction(assistant.id) || actionState(assistant.id) === "pending"}
              onclick={() => requestAssistantAction(assistant)}>
              <HudIcon name={localAssistantInstalled(assistant.id) ? "uninstall" : "add"} size={17} />
              {actionLabel(assistant.id)}
            </button>

            {#if actionState(assistant.id) === "sent" || actionState(assistant.id) === "error"}
              <p
                class:error={actionState(assistant.id) === "error"}
                class="install-status"
                role={actionState(assistant.id) === "error" ? "alert" : "status"}>
                {actionStatus(assistant.id)}
              </p>
            {/if}
          </div>
        {/if}
      </article>
    {/each}
  </div>

</section>

<style>
  .assistants-page { padding-top: 2.5rem; }
  .assistants-page.embedded { width: 100%; padding-top: 2px; }
  .assistants-page.embedded .assistant-grid { margin-top: 0; }

  .assistant-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 23rem));
    gap: 1rem;
    margin-top: 1.25rem;
  }
  .assistant-card {
    position: relative;
    display: flex;
    overflow: hidden;
    flex-direction: column;
    background: linear-gradient(180deg, var(--color-card-2), var(--color-card));
    clip-path: polygon(var(--cut) 0, 100% 0, 100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%, 0 100%, 0 var(--cut));
    box-shadow: inset 0 0 0 1px var(--color-border);
    transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s var(--ease-shimpz);
  }
  .assistant-card:hover, .assistant-card:focus-within {
    background: linear-gradient(180deg, color-mix(in oklab, var(--color-cyan) 5%, var(--color-card-2)), var(--color-card));
    transform: translateY(-2px);
  }
  .assistant-card.installed:hover, .assistant-card.installed:focus-within {
    background: linear-gradient(180deg, color-mix(in oklab, var(--color-green) 5%, var(--color-card-2)), var(--color-card));
  }
  .assistant-card.installed {
    box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-green) 58%, var(--color-border));
  }
  .assistant-details { display: flex; min-width: 0; flex: 1; flex-direction: column; padding: 1rem; }
  .assistant-heading { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.8rem; }
  .assistant-identity { min-width: 0; }
  .assistant-identity h2 { overflow: hidden; margin: 0; font-size: 1.05rem; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
  .assistant-link::after { position: absolute; z-index: 1; content: ""; inset: 0; }
  .assistant-identity p { overflow: hidden; margin: 0.25rem 0 0; color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.62rem; text-overflow: ellipsis; white-space: nowrap; }
  .free-badge {
    align-self: start;
    border: 1px solid color-mix(in oklab, var(--color-green) 38%, var(--color-border));
    padding: 0.22rem 0.4rem;
    color: var(--color-green);
    font-family: var(--font-mono);
    font-size: 0.54rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .assistant-summary {
    display: -webkit-box;
    margin: 0.5rem 0 0;
    overflow: hidden;
    color: var(--color-muted);
    font-size: 0.84rem;
    line-height: 1.55;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
  .assistant-action {
    position: absolute;
    z-index: 2;
    right: 0;
    bottom: 0;
    left: 0;
    padding: 2.5rem 1rem 1rem;
    background: linear-gradient(180deg, transparent, rgba(0, 0, 0, 0.96) 42%);
    opacity: 0;
    pointer-events: none;
    transform: translateY(0.4rem);
    transition: opacity 0.16s ease, transform 0.16s var(--ease-shimpz);
  }
  .assistant-card:hover .assistant-action,
  .assistant-card:focus-within .assistant-action,
  .assistant-action.persistent {
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
  }
  .install-action { width: 100%; min-height: 2.5rem; border: 0; padding: 0.6rem 0.75rem; cursor: pointer; font-size: 0.62rem; }
  .install-status { margin: 0.55rem 0 0; color: var(--color-green); font-size: 0.68rem; line-height: 1.45; }
  .install-status.error { color: var(--color-danger); }
  .context-error {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-top: 1rem;
    border-left: 2px solid var(--color-danger);
    padding: 0.65rem 0.75rem;
    background: color-mix(in oklab, var(--color-danger) 5%, #000);
    color: var(--color-danger);
    font-size: 0.68rem;
    line-height: 1.45;
  }
  .context-error button {
    min-height: 2rem;
    border: 1px solid color-mix(in oklab, var(--color-danger) 55%, var(--color-border));
    padding: 0 0.65rem;
    background: #000;
    color: var(--color-danger);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  @media (max-width: 720px) {
    .assistant-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 540px) {
    .assistant-grid { grid-template-columns: 1fr; }
    .context-error { align-items: stretch; flex-direction: column; }
  }
  @media (hover: none), (pointer: coarse) {
    .assistant-action {
      position: static;
      padding: 0.25rem 1rem 1rem;
      background: transparent;
      opacity: 1;
      pointer-events: auto;
      transform: none;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .assistant-card, .assistant-action { transition: none; }
    .assistant-card:hover, .assistant-card:focus-within { transform: none; }
  }
</style>
