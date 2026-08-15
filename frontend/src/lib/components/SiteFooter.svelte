<script lang="ts">
  import { SiteFooter as PublicSiteFooter } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { lang, statement }: { lang: Locale; statement?: string } = $props();
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
  {statement}
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
    margin-inline: 5.625rem;
    transform: scale(6);
  }
  :global([data-slot="site-footer"] [data-slot="shimpz-brand-wordmark"]) { display: none; }

  @media (max-width: 620px) {
    :global([data-slot="site-footer"] .utility) {
      gap: 1rem;
      margin-block-start: 1.5rem;
    }

    :global([data-slot="site-footer"] .shimpz-brand) {
      width: 100%;
      min-height: 13.5rem;
      align-items: center;
      justify-content: center;
    }

    :global([data-slot="site-footer"] .brand > p) {
      width: 100%;
      text-align: center;
    }

    :global([data-slot="site-footer"] nav) {
      display: grid;
      width: 100%;
      grid-template-columns: max-content max-content;
      justify-content: space-evenly;
      gap: 0;
    }

    :global([data-slot="site-footer"] nav [data-slot="site-footer-group"]) {
      width: auto;
      min-width: 0;
      justify-items: end;
      text-align: right;
    }

    :global([data-slot="site-footer-group-title"]) {
      font-size: clamp(0.58rem, 2.6vw, 0.72rem);
    }

    :global([data-slot="site-footer-group"] a) {
      font-size: clamp(0.64rem, 2.8vw, 0.78rem);
    }
  }
</style>
