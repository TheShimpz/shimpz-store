<script lang="ts">
  let { size = 64 }: { size?: number } = $props();
</script>

<span class="app-icon assistant-icon" style={`width:${size}px;height:${size}px`} aria-hidden="true">
  <svg viewBox="0 0 48 48" fill="none" role="presentation">
    <path class="frame" d="M8 8h32v32H8z" />
    <path class="pulse" d="M4 25h9l4-11 7 22 6-17 4 6h10" />
    <circle cx="24" cy="24" r="18" class="orbit" />
  </svg>
</span>

<style>
  .assistant-icon {
    --g1: var(--color-cyan-strong);
    --g2: var(--color-magenta);
    color: #ffffff;
  }
  svg { position: relative; z-index: 1; width: 68%; height: 68%; filter: drop-shadow(0 0 5px rgba(0, 240, 255, 0.42)); }
  .frame, .orbit { stroke: currentColor; stroke-width: 1.4; opacity: 0.34; }
  .orbit { stroke-dasharray: 2 4; }
  .pulse { stroke: currentColor; stroke-width: 2.2; stroke-linecap: square; stroke-linejoin: bevel; }
</style>
