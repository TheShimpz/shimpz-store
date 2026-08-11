<script lang="ts">
  import { onMount } from "svelte";
  import { ActionLink, AssistantIcon } from "@shimpz/frontend";
  import { parseAssistantCatalog } from "$lib/assistantCatalog.js";
  import { formatCatalogCount, type HomepageContent } from "$lib/homepage";

  type CatalogAssistant = {
    id: string;
    name: string;
    summary: string;
    providers: readonly string[];
    sourceDigest: string;
    iconDigest: string;
  };

  let { content, catalogHref }: { content: HomepageContent; catalogHref: string } = $props();
  let assistants = $state<readonly CatalogAssistant[]>([]);
  let catalogState = $state<"loading" | "ready" | "error">("loading");

  function countHeading(): string {
    return formatCatalogCount(content, assistants.length);
  }

  function category(assistant: CatalogAssistant): string {
    return assistant.providers.length > 0 ? assistant.providers.join(" · ") : content.catalogCore;
  }

  async function loadCatalog() {
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

  onMount(() => {
    void loadCatalog();
  });
</script>

<section class="catalog" aria-labelledby="catalog-title" data-slot="homepage-catalog">
  <header>
    <h2 id="catalog-title">{catalogState === "ready" ? countHeading() : content.catalogHeading}</h2>
  </header>

  <div
    class="catalog-stage"
    class:empty={catalogState === "ready" && assistants.length === 0}
    aria-busy={catalogState === "loading"}
  >
    {#if catalogState === "error"}
      <div class="catalog-error" role="alert">
        <span>{content.catalogUnavailable}</span>
        <button type="button" onclick={loadCatalog}>{content.catalogRetry}</button>
      </div>
    {:else if catalogState === "ready" && assistants.length > 0}
      <div class="catalog-grid">
        {#each assistants as assistant (assistant.id)}
          <article>
            <div class="identity">
              <AssistantIcon
                assistant={assistant.id}
                size={56}
                src={`/api/assistant-icons/${assistant.sourceDigest.slice(7)}/${assistant.iconDigest.slice(7)}.png`}
              />
              <p class="category">{category(assistant)}</p>
            </div>
            <h3>{assistant.name}</h3>
            <p class="summary">{assistant.summary}</p>
          </article>
        {/each}
      </div>
    {/if}
  </div>

  <div class="catalog-action">
    <ActionLink href={catalogHref} variant="primary">{content.catalogCta} →</ActionLink>
  </div>
</section>

<style>
  .catalog { padding-block: clamp(5rem, 10vw, 9rem); }
  h2 {
    max-width: var(--shimpz-type-section-measure);
    margin: 0;
    font: 650 var(--shimpz-type-section-size)/var(--shimpz-type-section-leading) var(--shimpz-font-sans);
    letter-spacing: var(--shimpz-type-section-tracking);
    text-wrap: balance;
  }
  .catalog-stage { min-height: 13rem; margin-block-start: clamp(2rem, 5vw, 4rem); }
  .catalog-stage.empty { min-height: 0; margin-block-start: 0; }
  .catalog-action { margin-block-start: var(--shimpz-space-6); }
  .catalog-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--color-border); }
  article { min-width: 0; min-height: 16rem; padding: 1.4rem; border-inline-end: 1px solid var(--color-border); }
  article:nth-child(3n) { border-inline-end: 0; }
  article:nth-child(n + 4) { border-block-start: 1px solid var(--color-border); }
  .identity { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 1rem; }
  .category {
    min-width: 0;
    max-width: 70%;
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--color-cyan);
    font: 600 .68rem/1.4 var(--font-mono);
    letter-spacing: .15em;
    text-align: end;
    text-transform: uppercase;
  }
  h3 { margin: 3.5rem 0 .7rem; font-size: 1.15rem; line-height: 1.2; }
  .summary { max-width: 44ch; margin: 0; color: var(--color-muted); font-size: .9rem; line-height: 1.65; }
  .catalog-error { display: flex; min-height: 8rem; align-items: center; justify-content: space-between; gap: 1rem; padding: 1.25rem; color: var(--color-muted); border: 1px solid var(--color-border); }
  button { min-height: var(--shimpz-control-height); padding: .65rem .9rem; color: var(--color-cyan); font: 700 .7rem/1 var(--font-mono); letter-spacing: .08em; text-transform: uppercase; background: transparent; border: 1px solid var(--color-cyan); cursor: pointer; }
  button:focus-visible { outline: 2px solid var(--color-yellow); outline-offset: 3px; }
  @media (max-width: 900px) {
    .catalog-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    article:nth-child(3n) { border-inline-end: 1px solid var(--color-border); }
    article:nth-child(2n) { border-inline-end: 0; }
    article:nth-child(n + 3) { border-block-start: 1px solid var(--color-border); }
  }
  @media (max-width: 620px) {
    .catalog-grid { grid-template-columns: 1fr; }
    article { min-height: auto; border-inline-end: 0; border-block-start: 1px solid var(--color-border); }
    article:first-child { border-block-start: 0; }
    article:nth-child(3n) { border-inline-end: 0; }
    .catalog-error { align-items: flex-start; flex-direction: column; }
  }
</style>
