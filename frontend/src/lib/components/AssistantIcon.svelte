<script lang="ts">
  let { size = 64, src }: { size?: number; src?: string } = $props();
  let imageFailed = $state(false);

  $effect(() => {
    src;
    imageFailed = false;
  });
</script>

<span class={["assistant-icon-tile", "assistant-icon", src && !imageFailed && "has-image"]} style={`width:${size}px;height:${size}px`} aria-hidden="true">
  {#if src && !imageFailed}
    <img {src} alt="" decoding="async" onerror={() => (imageFailed = true)} />
  {:else}<svg viewBox="0 0 48 48" fill="none" role="presentation">
    <path class="frame" d="M8 8h32v32H8z" />
    <path class="pulse" d="M4 25h9l4-11 7 22 6-17 4 6h10" />
    <circle cx="24" cy="24" r="18" class="orbit" />
  </svg>{/if}
</span>

<style>
  .assistant-icon {
    --g1: var(--color-cyan-strong);
    --g2: var(--color-magenta);
    color: #ffffff;
  }
  .has-image { overflow: visible; background: transparent; box-shadow: none; clip-path: none; text-shadow: none; }
  .has-image::after { content: none; }
  svg { position: relative; z-index: 1; width: 68%; height: 68%; filter: drop-shadow(0 0 5px rgba(0, 240, 255, 0.42)); }
  img { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: contain; }
  .frame, .orbit { stroke: currentColor; stroke-width: 1.4; opacity: 0.34; }
  .orbit { stroke-dasharray: 2 4; }
  .pulse { stroke: currentColor; stroke-width: 2.2; stroke-linecap: square; stroke-linejoin: bevel; }
</style>
