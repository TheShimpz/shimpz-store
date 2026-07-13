<script lang="ts">
  type Crumb = { label: string; href?: string };
  let { items }: { items: Crumb[] } = $props();
</script>

<nav aria-label="Breadcrumb" class="mb-6 flex flex-wrap items-center gap-2 text-sm dim">
  {#each items as c, i (i)}
    {#if i > 0}<span aria-hidden="true">/</span>{/if}
    {#if c.href && i < items.length - 1}
      <a href={c.href} class="transition hover:text-[var(--color-fg)]">{c.label}</a>
    {:else}
      <span class="text-[var(--color-fg)]">{c.label}</span>
    {/if}
  {/each}
</nav>
