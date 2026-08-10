<script lang="ts">
  import { SiteFooter as PublicSiteFooter } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { lang }: { lang: Locale } = $props();
</script>

{#snippet links()}
  <a href="/privacy">{tr("privacy", lang)}</a>
  <a href="/terms">{tr("terms", lang)}</a>
  <a href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer">{tr("nav_docs", lang)} ↗</a>
  <a href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
{/snippet}

{#snippet meta()}
  <i aria-hidden="true"></i>
  <span>Space platform // open source</span>
{/snippet}

<PublicSiteFooter
  brandHref={u.home(lang)}
  brandAriaLabel="Shimpz home"
  linksLabel={tr("footer_links", lang)}
  statement={tr("footer", lang)}
  {links}
  {meta}
/>

<style>
  i { width: .42rem; height: .42rem; background: var(--color-green); border-radius: 50%; box-shadow: 0 0 8px rgba(5,255,161,.55); }
</style>
