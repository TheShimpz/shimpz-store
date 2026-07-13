<script lang="ts">
  // Apple-store-style rounded app icon: a warm gradient squircle with the glyph. The gradient is derived
  // from the id, so every app/driver gets a stable, distinct, on-brand warm tile — no third-party logos.
  let { glyph, id, size = 44, brand }: { glyph: string; id: string; size?: number; brand?: string } =
    $props();

  const NEON: [string, string][] = [
    ["#00f0ff", "#7c3aed"],
    ["#ff2a6d", "#7c3aed"],
    ["#00f0ff", "#05ffa1"],
    ["#ff2a6d", "#00f0ff"],
    ["#fcee0a", "#ff2a6d"],
    ["#05ffa1", "#00f0ff"],
    ["#a855f7", "#ff2a6d"],
    ["#00eaff", "#ff2a6d"],
  ];
  const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  // third-party drivers → their official BRAND COLOUR (recognition); everything else → the neon family
  const g = $derived<[string, string]>(
    brand
      ? [`color-mix(in oklab, ${brand} 92%, white)`, `color-mix(in oklab, ${brand} 80%, black)`]
      : NEON[hash(id) % NEON.length],
  );
</script>

<span
  class="app-icon"
  style="--g1:{g[0]}; --g2:{g[1]}; width:{size}px; height:{size}px; font-size:{Math.round(size * 0.5)}px; line-height:1"
  aria-hidden="true"
>{glyph}</span>
