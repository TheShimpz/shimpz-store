<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { onMount } from "svelte";
  import { PageIntro } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { parseAssistantCatalog } from "$lib/assistantCatalog.js";
  import { requestedAssistantFromSearch } from "$lib/cloudAssistantLifecycle.js";
  import AssistantStore from "$lib/components/AssistantStore.svelte";
  import AssistantDetail from "$lib/components/AssistantDetail.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  type CatalogAssistant = ReturnType<typeof parseAssistantCatalog>[number];
  let assistants = $state<readonly CatalogAssistant[]>([]);
  let catalogState = $state<"loading" | "ready" | "error">("loading");
  const requestedAssistant = $derived(browser ? requestedAssistantFromSearch(page.url.search) : "");
  const assistant = $derived(assistants.find(({ id }) => id === requestedAssistant));

  async function loadAssistantCatalog() {
    catalogState = "loading";
    try {
      const response = await fetch("/api/assistants", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      assistants = parseAssistantCatalog(await response.json());
      catalogState = "ready";
    } catch {
      assistants = [];
      catalogState = "error";
    }
  }

  onMount(() => { void loadAssistantCatalog(); });
</script>

<Seo
  title={`${assistant?.name ?? tr("assistants_title", lang)} · Shimpz`}
  description={assistant?.summary ?? tr("assistants_lead", lang)}
  {lang} />

{#if requestedAssistant}
  {#if catalogState === "loading"}
    <section class="wrap detail-state" aria-busy="true" aria-labelledby="assistant-loading-title">
      <a href={u.assistants(lang)}>← {tr("assistants_back_store", lang)}</a>
      <PageIntro titleId="assistant-loading-title" title={tr("assistants_catalog_loading", lang)} />
    </section>
  {:else if catalogState === "error"}
    <section class="wrap detail-state" aria-labelledby="assistant-error-title">
      <a href={u.assistants(lang)}>← {tr("assistants_back_store", lang)}</a>
      <PageIntro titleId="assistant-error-title" title={tr("assistants_catalog_unavailable", lang)} />
      <button type="button" onclick={loadAssistantCatalog}>{tr("assistants_catalog_retry", lang)}</button>
    </section>
  {:else if assistant}
    {#key requestedAssistant}<AssistantDetail {lang} {assistant} />{/key}
  {:else}
    <section class="wrap detail-state" aria-labelledby="assistant-missing-title">
      <a href={u.assistants(lang)}>← {tr("assistants_back_store", lang)}</a>
      <PageIntro
        titleId="assistant-missing-title"
        title={tr("assistants_detail_not_found", lang)}
        lead={tr("assistants_detail_not_found_help", lang)} />
    </section>
  {/if}
{:else}
  <AssistantStore {lang} {assistants} {catalogState} onRetry={loadAssistantCatalog} />
{/if}

<style>
  .detail-state { min-height: 50vh; padding-top: 2rem; }
  .detail-state > a { display: inline-block; margin-bottom: 1.25rem; color: var(--color-cyan); font-family: var(--font-mono); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
  .detail-state > button { min-height: 2.5rem; margin-top: 1rem; border: 0; padding: 0 1rem; background: var(--color-cyan); color: var(--color-accent-ink); cursor: pointer; font-family: var(--font-mono); font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
</style>
