<script lang="ts">
  import type { Locale } from "$lib/locales";
  import { tr } from "$lib/i18n";
  import { parseAssistantCatalog } from "$lib/assistantCatalog.js";
  import { closedAssistantStoreHref } from "$lib/assistantStoreUrl.js";
  import { AssistantCard, PageIntro } from "@shimpz/frontend";

  type CatalogAssistant = ReturnType<typeof parseAssistantCatalog>[number];

  let {
    lang,
    assistants = [],
    catalogState = "ready",
    onRetry = () => {},
  }: {
    lang: Locale;
    assistants?: readonly CatalogAssistant[];
    catalogState?: "loading" | "ready" | "error";
    onRetry?: () => void;
  } = $props();
</script>

<section class="wrap assistants-page" aria-labelledby="assistants-title">
  <PageIntro
    titleId="assistants-title"
    kicker={tr("assistants_preview", lang)}
    title={tr("assistants_title", lang)}
    lead={tr("assistants_lead", lang)} />

  {#if catalogState === "error"}
    <div class="context-error" role="alert">
      <span>{tr("assistants_catalog_unavailable", lang)}</span>
      <button type="button" onclick={onRetry}>
        {tr("assistants_catalog_retry", lang)}
      </button>
    </div>
  {/if}

  <div class="assistant-grid" aria-busy={catalogState === "loading"}>
    {#each assistants as assistant (assistant.id)}
      <AssistantCard
        id={`assistant-${assistant.id}`}
        class="assistant-card"
        name={assistant.name}
        meta={assistant.creators.join(", ")}
        summary={assistant.summary}
        iconSrc={`/api/assistant-icons/${assistant.sourceDigest.slice(7)}/${assistant.iconDigest.slice(7)}.png`}
        badge={tr("assistants_free", lang)}
        href={closedAssistantStoreHref(lang, assistant.id)}
      />
    {/each}
  </div>

</section>

<style>
  .assistants-page { padding-top: 2.5rem; }

  .assistant-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 23rem));
    gap: 1rem;
    margin-top: 1.25rem;
  }
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
</style>
