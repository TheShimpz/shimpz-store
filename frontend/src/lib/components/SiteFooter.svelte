<script lang="ts">
  import { SiteFooter as PublicSiteFooter } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { lang }: { lang: Locale } = $props();
</script>

{#snippet links()}
  <div data-slot="site-footer-group">
    <p data-slot="site-footer-group-title">{tr("footer_group_project", lang)}</p>
    <a href={u.openSource(lang)}>{tr("nav_open_source", lang)}</a>
    <a href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer">{tr("nav_docs", lang)} ↗</a>
    <a href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
  </div>
  <div data-slot="site-footer-group">
    <p data-slot="site-footer-group-title">{tr("footer_group_company", lang)}</p>
    <a href={u.about(lang)}>{tr("nav_about", lang)}</a>
    <a href="/privacy">{tr("privacy", lang)}</a>
    <a href="/terms">{tr("terms", lang)}</a>
  </div>
{/snippet}

<PublicSiteFooter
  brandHref={u.home(lang)}
  brandAriaLabel={tr("brand_home", lang)}
  linksLabel={tr("footer_links", lang)}
  contentWidth="editorial"
  {links}
/>

<style>
  :global([data-slot="site-footer"].shimpz-site-footer) {
    position: relative;
    z-index: 1;
    background: transparent;
  }
  :global([data-slot="site-footer-monument"]) { opacity: 0.3; }
  :global([data-slot="site-footer"] [data-slot="shimpz-brand-mark"]) {
    margin-inline: 2.25rem;
    transform: scale(3);
  }
</style>
