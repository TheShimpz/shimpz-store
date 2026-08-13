<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount, tick } from "svelte";
  import { AssistantIcon, SignalList } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { parseAssistantCatalog } from "$lib/assistantCatalog.js";
  import {
    closedAssistantLoginHref,
    closedAssistantTeamHref,
    cloudAssistantAction,
    cloudRequestIsCurrent,
    hostedAssistantStoreCanStart,
    parseCloudAccount,
    parseCloudAssistantInventory,
    parseCloudTeams,
    selectCloudTeam,
  } from "$lib/cloudAssistantLifecycle.js";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import HudIcon from "$lib/components/HudIcon.svelte";

  type ActionKind = "install" | "uninstall";
  type CloudPhase = "checking" | "unauthenticated" | "empty" | "ready" | "error";
  type CloudInventoryState = "idle" | "loading" | "ready" | "error";
  type CloudTeam = { team_id: string; team_name: string };
  type CatalogAssistant = ReturnType<typeof parseAssistantCatalog>[number];

  const ACTION_BATCH_SIZE = 12;

  let { lang, assistant }: { lang: Locale; assistant: CatalogAssistant } = $props();
  let cloudPhase = $state<CloudPhase>("checking");
  let cloudInventoryState = $state<CloudInventoryState>("idle");
  let cloudTeams = $state<CloudTeam[]>([]);
  let cloudSelectedTeam = $state("");
  let cloudInstalledAssistantIds = $state<string[]>([]);
  let cloudActionLatch = $state(false);
  let cloudPendingAction = $state<ActionKind | "">("");
  let cloudFeedback = $state<"" | "success" | "error">("");
  let actionQuery = $state("");
  let visibleActionCount = $state(ACTION_BATCH_SIZE);
  let showAllActions = $state(false);
  let actionResultsStatus = $state<HTMLParagraphElement>();
  let cloudGeneration = 0;
  const cloudTargetTeam = $derived(cloudTeams.find((team) => team.team_id === cloudSelectedTeam));
  const normalizedActionQuery = $derived(actionQuery.trim().toLowerCase());
  const filteredActions = $derived(assistant.actions.filter((action) =>
    !normalizedActionQuery ||
    action.id.toLowerCase().includes(normalizedActionQuery) ||
    action.integrations.some((integration) => integration.toLowerCase().includes(normalizedActionQuery)) ||
    action.humanRequests.some((request) => request.toLowerCase().includes(normalizedActionQuery))
  ));
  const visibleActions = $derived(
    showAllActions ? filteredActions : filteredActions.slice(0, visibleActionCount),
  );
  const actionSearchVisible = $derived(assistant.actions.length > ACTION_BATCH_SIZE);
  const moreActionsAvailable = $derived(
    !showAllActions && visibleActions.length < filteredActions.length,
  );

  function searchActions(event: Event) {
    actionQuery = (event.currentTarget as HTMLInputElement).value;
    visibleActionCount = ACTION_BATCH_SIZE;
  }

  async function focusActionResults() {
    await tick();
    actionResultsStatus?.focus();
  }

  async function showMoreDeclaredActions() {
    visibleActionCount = Math.min(
      visibleActionCount + ACTION_BATCH_SIZE,
      filteredActions.length,
    );
    if (visibleActionCount === filteredActions.length) await focusActionResults();
  }

  async function showEveryDeclaredAction() {
    showAllActions = true;
    await focusActionResults();
  }

  function cloudAssistantInstalled(): boolean {
    return cloudAssistantAction(
      cloudInventoryState === "ready",
      cloudInstalledAssistantIds,
      assistant.id,
    ) === "uninstall";
  }

  function clearCloudSession() {
    cloudGeneration += 1;
    cloudPhase = "unauthenticated";
    cloudInventoryState = "idle";
    cloudTeams = [];
    cloudSelectedTeam = "";
    cloudInstalledAssistantIds = [];
    cloudFeedback = "";
    localStorage.removeItem("shimpz_current_team");
    localStorage.removeItem("shimpz_current_team_name");
  }

  async function loadCloudInventory(teamId: string, generation: number): Promise<string[] | null> {
    if (!cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) return null;
    cloudInventoryState = "loading";
    cloudInstalledAssistantIds = [];
    try {
      const response = await fetch(`/api/teams/${encodeURIComponent(teamId)}/assistants`, {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (!cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) return null;
      if (response.status === 401) {
        clearCloudSession();
        return null;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const installed = parseCloudAssistantInventory(await response.json());
      if (!cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) return null;
      cloudInstalledAssistantIds = installed;
      cloudInventoryState = "ready";
      return installed;
    } catch {
      if (cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) {
        cloudInstalledAssistantIds = [];
        cloudInventoryState = "error";
      }
      return null;
    }
  }

  async function bootCloudStore() {
    if (!hostedAssistantStoreCanStart(window.top === window.self)) {
      cloudPhase = "error";
      return;
    }
    const generation = ++cloudGeneration;
    cloudPhase = "checking";
    cloudInventoryState = "idle";
    cloudTeams = [];
    cloudSelectedTeam = "";
    cloudInstalledAssistantIds = [];
    cloudFeedback = "";
    try {
      const meResponse = await fetch("/api/me", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (generation !== cloudGeneration) return;
      if (meResponse.status === 401) {
        clearCloudSession();
        return;
      }
      if (!meResponse.ok) throw new Error(`HTTP ${meResponse.status}`);
      const account = parseCloudAccount(await meResponse.json());
      if (!account.authenticated) {
        clearCloudSession();
        return;
      }

      const teamResponse = await fetch("/api/teams", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (generation !== cloudGeneration) return;
      if (teamResponse.status === 401) {
        clearCloudSession();
        return;
      }
      if (!teamResponse.ok) throw new Error(`HTTP ${teamResponse.status}`);
      const teams = parseCloudTeams(await teamResponse.json());
      if (generation !== cloudGeneration) return;
      cloudTeams = teams;
      if (teams.length === 0) {
        cloudPhase = "empty";
        return;
      }
      cloudPhase = "ready";
      const remembered = selectCloudTeam(teams, localStorage.getItem("shimpz_current_team") ?? "");
      if (!remembered) return;
      cloudSelectedTeam = remembered;
      const team = teams.find((candidate) => candidate.team_id === remembered);
      localStorage.setItem("shimpz_current_team_name", team?.team_name ?? remembered);
      await loadCloudInventory(remembered, generation);
    } catch {
      if (generation === cloudGeneration) cloudPhase = "error";
    }
  }

  async function chooseCloudTeam(event: Event) {
    if (cloudActionLatch) return;
    const selected = selectCloudTeam(cloudTeams, (event.currentTarget as HTMLSelectElement).value);
    cloudSelectedTeam = selected;
    cloudInventoryState = "idle";
    cloudInstalledAssistantIds = [];
    cloudFeedback = "";
    const generation = ++cloudGeneration;
    if (!selected) {
      localStorage.removeItem("shimpz_current_team");
      localStorage.removeItem("shimpz_current_team_name");
      return;
    }
    const team = cloudTeams.find((value) => value.team_id === selected);
    localStorage.setItem("shimpz_current_team", selected);
    localStorage.setItem("shimpz_current_team_name", team?.team_name ?? selected);
    await loadCloudInventory(selected, generation);
  }

  async function retryCloudInventory() {
    if (!cloudSelectedTeam || cloudActionLatch) return;
    cloudFeedback = "";
    const generation = ++cloudGeneration;
    await loadCloudInventory(cloudSelectedTeam, generation);
  }

  async function mutateCloudAssistant() {
    if (
      !hostedAssistantStoreCanStart(window.top === window.self) ||
      cloudActionLatch ||
      !cloudSelectedTeam ||
      cloudInventoryState !== "ready"
    ) return;
    const action = cloudAssistantAction(true, cloudInstalledAssistantIds, assistant.id);
    if (action === "blocked") return;
    const teamId = cloudSelectedTeam;
    const teamName = cloudTargetTeam?.team_name ?? teamId;
    if (
      action === "uninstall" &&
      !window.confirm(
        lang === "pt"
          ? `Desinstalar ${assistant.id} do Time ${teamName}?`
          : `Uninstall ${assistant.id} from Team ${teamName}?`,
      )
    ) return;

    cloudActionLatch = true;
    cloudPendingAction = action;
    cloudFeedback = "";
    const generation = cloudGeneration;
    try {
      const base = `/api/teams/${encodeURIComponent(teamId)}/assistants`;
      const response = action === "install"
        ? await fetch(base, {
            method: "POST",
            headers: { Accept: "application/json", "Content-Type": "application/json" },
            body: JSON.stringify({ assistant_id: assistant.id, source_digest: assistant.sourceDigest }),
          })
        : await fetch(`${base}/${encodeURIComponent(assistant.id)}`, {
            method: "DELETE",
            headers: { Accept: "application/json" },
          });
      if (!cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) return;
      if (response.status === 401) {
        clearCloudSession();
        return;
      }
    } catch {
      // The authoritative inventory refresh below decides what committed.
    } finally {
      if (cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) {
        const installed = await loadCloudInventory(teamId, generation);
        if (installed && cloudRequestIsCurrent(generation, cloudGeneration, teamId, cloudSelectedTeam)) {
          const nextAction = cloudAssistantAction(true, installed, assistant.id);
          const committed = action === "install" ? nextAction === "uninstall" : nextAction === "install";
          cloudFeedback = committed ? "success" : "error";
        }
      }
      cloudActionLatch = false;
      cloudPendingAction = "";
    }
  }

  function cloudButtonLabel(): string {
    if (cloudActionLatch) {
      return tr(cloudPendingAction === "uninstall" ? "assistants_cloud_uninstalling" : "assistants_cloud_installing", lang);
    }
    if (cloudPhase === "checking") return tr("assistants_cloud_loading", lang);
    if (cloudPhase === "unauthenticated") return tr("assistants_cloud_sign_in", lang);
    if (cloudPhase === "empty") return tr("assistants_cloud_create_team", lang);
    if (cloudPhase === "error") return tr("assistants_cloud_retry", lang);
    if (!cloudSelectedTeam) return tr("assistants_cloud_choose", lang);
    if (cloudInventoryState === "loading" || cloudInventoryState === "idle") {
      return tr("assistants_inventory_loading", lang);
    }
    if (cloudInventoryState === "error") return tr("assistants_cloud_retry_inventory", lang);
    return tr(cloudAssistantInstalled() ? "assistants_cloud_uninstall" : "assistants_cloud_install", lang);
  }

  function cloudButtonDisabled(): boolean {
    return cloudPhase === "checking" || cloudActionLatch ||
      (cloudPhase === "ready" && (
        !cloudSelectedTeam || cloudInventoryState === "loading" || cloudInventoryState === "idle"
      ));
  }

  async function cloudPrimaryAction() {
    if (cloudPhase === "unauthenticated") {
      await goto(closedAssistantLoginHref(lang, assistant.id));
      return;
    }
    if (cloudPhase === "empty") {
      await goto(closedAssistantTeamHref(lang, assistant.id));
      return;
    }
    if (cloudPhase === "error") {
      await bootCloudStore();
      return;
    }
    if (cloudInventoryState === "error") {
      await retryCloudInventory();
      return;
    }
    await mutateCloudAssistant();
  }

  onMount(() => {
    void bootCloudStore();
    return () => { cloudGeneration += 1; };
  });
</script>

{#snippet actionSignal(action: CatalogAssistant["actions"][number])}
  <div class="action-name">
    <span>{tr("assistants_action", lang)}</span>
    <code>{action.id}</code>
  </div>
{/snippet}

{#snippet actionMeta(action: CatalogAssistant["actions"][number])}
  <dl class="action-meta">
    <div>
      <dt>{tr("assistants_integrations", lang)}</dt>
      <dd class:empty-value={!action.integrations.length}>
        {action.integrations.length ? action.integrations.join(", ") : tr("assistants_none", lang)}
      </dd>
    </div>
    <div>
      <dt>{tr("assistants_human_requests", lang)}</dt>
      <dd class:empty-value={!action.humanRequests.length}>
        {action.humanRequests.length ? action.humanRequests.join(", ") : tr("assistants_none", lang)}
      </dd>
    </div>
  </dl>
{/snippet}

<section class="wrap assistant-detail" aria-labelledby="assistant-detail-title">
  <a class="back-link" href={u.assistants(lang)}>← {tr("assistants_back_store", lang)}</a>

  <div class="detail-layout">
    <header class="assistant-hero">
      <AssistantIcon
        size={112}
        src={`/api/assistant-icons/${assistant.sourceDigest.slice(7)}/${assistant.iconDigest.slice(7)}.png`}
      />
      <div class="assistant-intro">
        <p class="kicker">{tr("assistants_detail_published", lang)}</p>
        <h1 id="assistant-detail-title">{assistant.name}</h1>
        <p class="creators">{assistant.creators.join(", ")}</p>
        <p class="summary">{assistant.summary}</p>
      </div>
    </header>

    <div class="detail-sidebar">
      <aside class="install-panel sidebar-panel" aria-labelledby="install-title">
        <div class="install-heading">
          <div>
            <p class="kicker">{tr("assistants_free", lang)}</p>
            <h2 id="install-title">{tr("assistants_install_title", lang)}</h2>
          </div>
          {#if cloudAssistantInstalled()}<span class="installed-dot" aria-hidden="true"></span>{/if}
        </div>
        {#if cloudPhase === "ready"}
          <label>
            <span>{tr("assistants_cloud_target_label", lang)}</span>
            <select value={cloudSelectedTeam} disabled={cloudActionLatch} onchange={chooseCloudTeam}>
              <option value="">{tr("assistants_cloud_choose", lang)}</option>
              {#each cloudTeams as team (team.team_id)}
                <option value={team.team_id}>{team.team_name}</option>
              {/each}
            </select>
          </label>
        {:else if cloudPhase === "unauthenticated"}
          <p>{tr("assistants_cloud_sign_in_help", lang)}</p>
        {:else if cloudPhase === "empty"}
          <p>{tr("assistants_cloud_no_teams", lang)}</p>
        {:else if cloudPhase === "error"}
          <p class="error" role="alert">{tr("assistants_cloud_load_failed", lang)}</p>
        {/if}
        <button
          class:btn-primary={!cloudAssistantInstalled()}
          class:btn-danger={cloudAssistantInstalled()}
          type="button"
          disabled={cloudButtonDisabled()}
          onclick={cloudPrimaryAction}>
          <HudIcon name={cloudAssistantInstalled() ? "uninstall" : "add"} size={17} />
          {cloudButtonLabel()}
        </button>
        {#if cloudFeedback}
          <p class:error={cloudFeedback === "error"} class="feedback" role={cloudFeedback === "error" ? "alert" : "status"}>
            {tr(cloudFeedback === "success" ? "assistants_cloud_committed" : "assistants_cloud_failed", lang)}
          </p>
        {/if}
      </aside>

      <div class="facts">
        <section class="sidebar-panel" aria-labelledby="access-title">
          <h2 id="access-title">{tr("assistants_permissions", lang)}</h2>
          <h3>{tr("assistants_integrations", lang)}</h3>
          {#if assistant.integrations.length}
            <ul>
              {#each assistant.integrations as integration (integration.id)}
                <li>
                  <strong>{integration.provider}</strong>
                  <span>{integration.scopes.length ? integration.scopes.join(", ") : tr("assistants_none", lang)}</span>
                </li>
              {/each}
            </ul>
          {:else}
            <p>{tr("assistants_none", lang)}</p>
          {/if}
          <h3>{tr("assistants_allowed_hosts", lang)}</h3>
          {#if assistant.allowedHosts.length}
            <ul class="hosts">
              {#each assistant.allowedHosts as host (host)}<li><code>{host}</code></li>{/each}
            </ul>
          {:else}
            <p>{tr("assistants_none", lang)}</p>
          {/if}
        </section>
        <section class="metadata sidebar-panel" aria-labelledby="info-title">
          <h2 id="info-title">{tr("assistants_information", lang)}</h2>
          <dl>
            <div><dt>{tr("assistants_version", lang)}</dt><dd>{assistant.version}</dd></div>
            <div><dt>{tr("assistants_architectures", lang)}</dt><dd>{assistant.platforms.join(", ")}</dd></div>
            <div><dt>{tr("assistants_repository", lang)}</dt><dd><a href={assistant.github} target="_blank" rel="noopener noreferrer">GitHub ↗</a></dd></div>
          </dl>
        </section>
      </div>
    </div>

    <div class="actions-column">
      <section aria-labelledby="actions-title">
        <div class="section-heading">
          <h2 id="actions-title">{tr("assistants_detail_actions", lang)}</h2>
          <span>{assistant.actions.length}</span>
        </div>
        {#if actionSearchVisible}
          <div class="action-tools">
            <label class="action-search" for="assistant-action-search">
              <span>{tr("assistants_actions_search", lang)}</span>
              <input
                id="assistant-action-search"
                type="search"
                value={actionQuery}
                placeholder={tr("assistants_actions_search_hint", lang)}
                aria-controls="assistant-actions-list"
                autocomplete="off"
                spellcheck="false"
                oninput={searchActions}
              />
            </label>
            <p
              class="action-results-status"
              class:no-results={filteredActions.length === 0}
              bind:this={actionResultsStatus}
              aria-live="polite"
              aria-atomic="true"
              tabindex="-1"
            >
              {#if filteredActions.length}
                {tr("assistants_actions_showing", lang)} {visibleActions.length}
                {tr("assistants_actions_of", lang)} {filteredActions.length}
              {:else}
                {tr("assistants_actions_no_matches", lang)}
              {/if}
            </p>
          </div>
        {/if}
        <SignalList
          id="assistant-actions-list"
          style="margin-top: 1rem; --signal-list-cut: var(--cut); --signal-list-border: var(--color-border);"
          items={visibleActions}
          getKey={(action) => action.id}
          signal={actionSignal}
          meta={actionMeta}
          aria-labelledby="actions-title"
        />
        {#if moreActionsAvailable}
          <div class="action-reveal">
            <button type="button" onclick={showMoreDeclaredActions}>
              {tr("assistants_actions_show_more", lang)}
            </button>
            <button type="button" onclick={showEveryDeclaredAction}>
              {tr("assistants_actions_show_all", lang)}
            </button>
          </div>
        {/if}
      </section>
    </div>
  </div>
</section>

<style>
  .assistant-detail { padding-top: 2rem; }
  .back-link { display: inline-block; margin-bottom: 1.25rem; color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
  .assistant-hero { display: grid; grid-column: 1; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: clamp(1.25rem, 4vw, 3rem); }
  .assistant-intro { min-width: 0; }
  .assistant-intro .kicker { margin: 0 0 0.45rem; }
  h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1; }
  .creators { margin: 0.45rem 0 0; color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.78rem; }
  .summary { max-width: 48rem; margin: 1rem 0 0; color: var(--color-muted); font-size: 1rem; line-height: 1.6; }
  .sidebar-panel { width: 100%; padding: 1rem; background: var(--color-card); box-shadow: inset 0 0 0 1px var(--color-border); }
  .install-heading { display: flex; align-items: start; justify-content: space-between; gap: 1rem; }
  .install-heading .kicker { margin: 0 0 0.25rem; color: var(--color-green); }
  .install-heading h2 { margin: 0; font-size: 1rem; }
  .installed-dot { width: 0.55rem; height: 0.55rem; margin-top: 0.35rem; background: var(--color-green); box-shadow: 0 0 10px color-mix(in oklab, var(--color-green) 55%, transparent); }
  .install-panel label { display: grid; gap: 0.35rem; margin-top: 1rem; }
  .install-panel label > span { color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.56rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
  .install-panel select { width: 100%; min-height: 2.6rem; border: 1px solid var(--color-border-strong); padding: 0 0.65rem; background: #050708; color: var(--color-fg); font-family: var(--font-mono); font-size: 0.7rem; }
  .install-panel > p { margin: 0.8rem 0 0; color: var(--color-muted); font-size: 0.72rem; line-height: 1.5; }
  .install-panel > p.error, .feedback.error { color: var(--color-danger); }
  .install-panel button { width: 100%; min-height: 2.6rem; margin-top: 1rem; border: 0; cursor: pointer; font-size: 0.62rem; }
  .feedback { color: var(--color-green); }
  .detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem); grid-template-rows: auto 1fr; column-gap: clamp(2rem, 6vw, 5rem); row-gap: 2.5rem; }
  .detail-sidebar { display: grid; grid-column: 2; grid-row: 1 / span 2; align-content: start; gap: 1rem; }
  .actions-column { grid-column: 1; }
  .section-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
  .section-heading h2, .facts h2 { margin: 0; font-size: 1.25rem; }
  .section-heading span { color: var(--color-cyan); font-family: var(--font-mono); }
  .action-tools { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-top: 1rem; }
  .action-search { display: grid; width: min(100%, 22rem); gap: 0.35rem; }
  .action-search span { color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.56rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
  .action-search input { width: 100%; min-height: 2.4rem; border: 1px solid var(--color-border-strong); padding: 0 0.75rem; background: #050708; color: var(--color-fg); font-family: var(--font-mono); font-size: 0.72rem; }
  .action-search input:focus-visible, .action-reveal button:focus-visible { outline: 2px solid var(--color-cyan); outline-offset: 2px; }
  .action-results-status { margin: 0 0 0.65rem; color: var(--color-muted); font-family: var(--font-mono); font-size: 0.68rem; }
  .action-results-status.no-results { color: var(--color-danger); }
  .action-results-status:focus { outline: 2px solid var(--color-cyan); outline-offset: 2px; }
  .action-name { display: grid; min-width: 0; gap: 0.2rem; }
  .action-name span { color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.56rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
  .action-name code { overflow-wrap: anywhere; color: var(--color-fg); font-size: 0.82rem; font-weight: 600; line-height: 1.4; }
  .action-meta { display: grid; min-width: 0; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .action-meta > div { min-width: 0; }
  .action-meta dd { margin-top: 0.2rem; }
  .empty-value { color: var(--color-muted-2); }
  .action-reveal { display: flex; justify-content: flex-end; gap: 0.65rem; margin-top: 0.75rem; }
  .action-reveal button { min-height: 2.2rem; border: 1px solid var(--color-border-strong); padding: 0 0.9rem; background: var(--color-card-2); color: var(--color-cyan); cursor: pointer; font-family: var(--font-mono); font-size: 0.6rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
  dl { margin: 0; }
  dt { color: var(--color-muted-2); font-family: var(--font-mono); font-size: 0.56rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
  dd { min-width: 0; margin: 0.2rem 0 0; overflow-wrap: anywhere; font-size: 0.72rem; line-height: 1.5; }
  .facts { display: grid; align-content: start; gap: 1rem; }
  .facts h3 { margin: 1rem 0 0.35rem; color: var(--color-muted-2); font-size: 0.62rem; letter-spacing: 0.06em; text-transform: uppercase; }
  .facts p { margin: 0; color: var(--color-muted); font-size: 0.72rem; }
  .facts ul { display: grid; gap: 0.45rem; margin: 0; padding: 0; list-style: none; }
  .facts li { min-width: 0; overflow-wrap: anywhere; font-size: 0.72rem; }
  .facts li strong, .facts li span { display: block; }
  .facts li span { color: var(--color-muted); }
  .hosts code { white-space: normal; }
  .metadata dl { display: grid; gap: 0.8rem; margin-top: 1rem; }
  .metadata dl > div { display: grid; grid-template-columns: minmax(7rem, 0.45fr) minmax(0, 1fr); gap: 0.75rem; }
  .metadata a { color: var(--color-cyan); }
  @media (max-width: 900px) {
    .detail-layout { grid-template-columns: 1fr; grid-template-rows: auto; column-gap: 0; row-gap: 2rem; }
    .assistant-hero, .detail-sidebar, .actions-column { grid-column: 1; grid-row: auto; }
  }
  @media (max-width: 540px) {
    .assistant-hero { grid-template-columns: 1fr; align-items: start; }
    .action-tools { display: grid; align-items: start; }
    .action-search { width: 100%; }
    .action-results-status { margin: 0; }
    .action-reveal { display: grid; grid-template-columns: 1fr 1fr; }
  }

  @container signal-list (max-width: 28rem) {
    .action-meta { grid-template-columns: minmax(0, 1fr); gap: 0.65rem; }
  }
</style>
