<script lang="ts">
  import { ShimpzBrand } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { lang }: { lang: Locale } = $props();
</script>

<footer data-slot="site-footer" class="site-footer">
  <div data-slot="site-footer-inner" class="inner">
    <div data-slot="site-footer-monument" class="monument" dir="ltr" aria-hidden="true">
      {#each [..."SHIMPZ"] as letter}<span>{letter}</span>{/each}
    </div>
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
    width: min(calc(100% - 2rem), var(--shimpz-editorial-width));
    min-height: clamp(24rem, 44vw, 36rem);
    padding-block: clamp(3rem, 7vw, 6rem) 2rem;
    margin-inline: auto;
  }
  .monument {
    display: flex;
    width: 100%;
    align-items: center;
    justify-content: space-between;
    color: var(--color-fg);
    font: 760 clamp(4rem, 18cqi, 15rem)/0.78 var(--font-sans);
    letter-spacing: -0.08em;
    opacity: 0.3;
  }
  .mark {
    display: flex;
    justify-content: center;
    margin-block-start: clamp(4rem, 8vw, 7rem);
  }
  .mark :global([data-slot="shimpz-brand-mark"]) {
    width: 9rem;
    height: 9rem;
  }
</style>
