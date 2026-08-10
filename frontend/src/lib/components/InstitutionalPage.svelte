<script lang="ts">
  import { Card, PageIntro } from "@shimpz/frontend";
  import type { InstitutionalPageContent } from "$lib/institutional";

  let { content }: { content: InstitutionalPageContent } = $props();
</script>

<section class="wrap institutional" aria-labelledby="institutional-title">
  <PageIntro
    kicker={content.kicker}
    titleId="institutional-title"
    title={content.title}
    lead={content.lead}
  />

  <div class="section-grid">
    {#each content.sections as section, index (section.title)}
      <Card class="institutional-card" tone={index === 0 ? "accent" : "default"}>
        <span>0{index + 1}</span>
        <h2>{section.title}</h2>
        <p>{section.body}</p>
      </Card>
    {/each}
  </div>

  <aside aria-labelledby="institutional-note-title">
    <p aria-hidden="true">Shimpz //</p>
    <div>
      <h2 id="institutional-note-title">{content.noteTitle}</h2>
      <p>{content.noteBody}</p>
    </div>
  </aside>
</section>

<style>
  .institutional { padding-block: clamp(3rem,8vw,7rem); }
  .section-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1rem; margin-block-start: clamp(3rem,7vw,6rem); }
  :global(.institutional-card) { min-height: 20rem; }
  :global(.institutional-card .content) { display: flex; height: 100%; flex-direction: column; }
  :global(.institutional-card .content > span) { color: var(--color-cyan); font: 600 .65rem/1 var(--font-mono); }
  :global(.institutional-card .content > h2) { margin: auto 0 1rem; font-size: clamp(1.35rem,2.5vw,2rem); line-height: 1.12; }
  :global(.institutional-card .content > p) { margin: 0; color: var(--color-muted); line-height: 1.7; }
  aside { display: grid; grid-template-columns: minmax(10rem,.35fr) minmax(0,1fr); gap: 2rem; padding: clamp(1.5rem,4vw,2.5rem); margin-block-start: 1rem; background: var(--color-surface); border: 1px solid var(--color-border); }
  aside > p { margin: 0; color: var(--color-cyan); font: 600 .65rem/1.4 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }
  aside h2 { margin: 0 0 .75rem; font-size: clamp(1.2rem,2vw,1.6rem); }
  aside div p { max-width: 64rem; margin: 0; color: var(--color-muted); line-height: 1.7; }
  @media (max-width: 820px) { .section-grid { grid-template-columns: 1fr; } :global(.institutional-card) { min-height: 15rem; } }
  @media (max-width: 520px) { aside { grid-template-columns: 1fr; } }
</style>
