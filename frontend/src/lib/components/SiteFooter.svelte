<script lang="ts">
  import { ShimpzBrand } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { lang }: { lang: Locale } = $props();
</script>

<footer data-slot="site-footer" class="site-footer">
  <div data-slot="site-footer-inner" class="inner">
    <div class="mark">
      <ShimpzBrand variant="symbol" href={u.home(lang)} ariaLabel={tr("brand_home", lang)} />
    </div>
  </div>
</footer>

<style>
  .site-footer {
    position: relative;
    z-index: 1;
    margin-block-start: clamp(5rem, 10vw, 8rem);
    background: transparent;
  }
  .inner {
    display: grid;
    width: min(calc(100% - 2rem), var(--shimpz-editorial-width));
    min-height: clamp(14rem, 30vw, 24rem);
    place-items: center;
    margin-inline: auto;
  }
  .mark :global([data-slot="shimpz-brand-mark"]) {
    width: 9rem;
    height: 9rem;
  }
</style>
