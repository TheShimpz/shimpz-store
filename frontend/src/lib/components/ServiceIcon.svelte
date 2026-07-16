<script lang="ts">
  import type { ServiceIconName } from "$lib/catalog";

  let {
    icon,
    size = 52,
    brand,
  }: { icon: ServiceIconName; size?: number; brand?: string } = $props();

  const accent = $derived(
    brand ? `color-mix(in oklab, ${brand} 72%, white)` : "var(--color-cyan)",
  );
  const secondary = $derived(
    icon === "edge" || icon === "object-storage" || icon === "secure-route"
      ? "var(--color-magenta)"
      : "var(--color-cyan)",
  );
</script>

<span
  class="service-icon"
  style={`--service-accent:${accent};--service-secondary:${secondary};width:${size}px;height:${size}px`}
  aria-hidden="true"
>
  <svg viewBox="0 0 64 64" focusable="false">
    <path class="plate" d="M14 3h36l11 11v36L50 61H14L3 50V14Z" />
    <path class="rail" d="M8 23v-7l8-8h8M56 41v7l-8 8h-8" />
    <path class="tick" d="M8 28v8M56 28v8" />

    {#if icon === "edge"}
      <path class="glyph" d="M15 39h33l5-6-5-8-8-1-5-7-10 2-4 7-6 2-4 6Z" />
      <path class="accent" d="M23 44 41 28M31 44l10-9" />
      <path class="node" d="M21 39h4v4h-4zM40 26h4v4h-4zM39 34h4v4h-4z" />
    {:else if icon === "database"}
      <path class="glyph" d="m18 19 6-4h16l6 4v26l-6 4H24l-6-4Z" />
      <path class="accent" d="m18 19 6 4h16l6-4M18 32l6 4h16l6-4M18 43l6 4h16l6-4" />
      <path class="node" d="M24 27h4v4h-4zM36 39h4v4h-4z" />
    {:else if icon === "event-bus"}
      <path class="glyph" d="M16 18h12v12H16zM36 34h12v12H36z" />
      <path class="accent" d="M28 24h10l5 5M36 40H26l-5-5" />
      <path class="node" d="m39 25 5 5-5 5zM25 30l-5 5 5 5z" />
    {:else if icon === "object-storage"}
      <path class="glyph" d="m32 14 17 9v19l-17 9-17-9V23Z" />
      <path class="accent" d="m15 23 17 9 17-9M32 32v19M23 19l17 9" />
      <path class="node" d="M29 29h6v6h-6z" />
    {:else if icon === "neural-media"}
      <path class="glyph" d="m32 14 14 8v18l-14 9-14-9V22Z" />
      <path class="accent" d="m32 20-7 7 7 5 7-5-7-7Zm0 12v10M25 27l-3 10M39 27l3 10" />
      <path class="node" d="M29 29h6v6h-6zM19 36h5v5h-5zM40 36h5v5h-5z" />
    {:else}
      <path class="glyph" d="m32 14 15 6v12c0 9-6 15-15 19-9-4-15-10-15-19V20Z" />
      <path class="accent" d="M23 32h8l5-6h7M28 41h7l5-6" />
      <path class="node" d="M20 29h5v6h-5zM40 23h5v6h-5zM38 32h5v6h-5z" />
    {/if}

    <path class="status" d="M13 52h9" />
    <path class="status-hot" d="M24 52h4" />
  </svg>
</span>

<style>
  .service-icon {
    position: relative;
    display: grid;
    flex: none;
    place-items: center;
    overflow: hidden;
    background:
      linear-gradient(135deg, color-mix(in oklab, var(--service-accent) 10%, transparent), transparent 48%),
      #050505;
    box-shadow:
      inset 0 0 0 1px color-mix(in oklab, var(--service-accent) 38%, var(--color-border)),
      inset 0 -16px 24px rgba(0, 0, 0, 0.48);
    clip-path: polygon(20% 0, 80% 0, 100% 20%, 100% 80%, 80% 100%, 20% 100%, 0 80%, 0 20%);
    color: var(--color-fg);
    isolation: isolate;
    transition: filter 160ms ease, box-shadow 160ms ease, transform 160ms ease;
  }

  .service-icon::before {
    position: absolute;
    z-index: -1;
    inset: 0;
    background: repeating-linear-gradient(0deg, transparent 0 5px, rgba(255, 255, 255, 0.025) 5px 6px);
    content: "";
  }

  svg { width: 100%; height: 100%; }
  path { vector-effect: non-scaling-stroke; }
  .plate { fill: none; stroke: color-mix(in oklab, var(--service-accent) 34%, transparent); stroke-width: 1; }
  .rail, .tick { fill: none; stroke: color-mix(in oklab, var(--service-secondary) 60%, transparent); stroke-width: 1; }
  .glyph, .accent {
    fill: none;
    stroke-linecap: square;
    stroke-linejoin: miter;
  }
  .glyph { stroke: currentColor; stroke-width: 1.8; }
  .accent { stroke: var(--service-accent); stroke-width: 1.35; }
  .node { fill: var(--service-accent); filter: drop-shadow(0 0 3px var(--service-accent)); }
  .status, .status-hot { fill: none; stroke-width: 1.2; }
  .status { stroke: color-mix(in oklab, var(--color-fg) 30%, transparent); }
  .status-hot { stroke: var(--service-secondary); }

  :global(.card:hover) .service-icon,
  :global(.card:focus-within) .service-icon {
    box-shadow:
      inset 0 0 0 1px color-mix(in oklab, var(--service-accent) 80%, var(--color-border)),
      0 0 18px color-mix(in oklab, var(--service-accent) 20%, transparent);
    filter: brightness(1.12);
    transform: translateY(-1px);
  }

  @media (prefers-reduced-motion: reduce) {
    .service-icon { transition: none; }
  }

  @media (forced-colors: active) {
    .service-icon { background: Canvas; box-shadow: inset 0 0 0 1px CanvasText; color: CanvasText; }
    .plate, .rail, .tick, .accent, .status, .status-hot { stroke: CanvasText; }
    .node { fill: CanvasText; filter: none; }
  }
</style>
