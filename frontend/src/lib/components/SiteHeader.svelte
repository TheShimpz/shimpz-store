<script lang="ts">
  import { ActionLink, DropdownMenu, SiteHeader as PublicSiteHeader, SiteNavLink } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import AccountMenu from "$lib/components/AccountMenu.svelte";
  import { tr } from "$lib/i18n";
  import { LOCALE_OPTIONS } from "$lib/locales";
  import { swapLocale, u } from "$lib/url";

  let { lang, path }: { lang: Locale; path: string } = $props();
  const currentLanguage = $derived(LOCALE_OPTIONS.find(({ code }) => code === lang)?.label ?? "English");
  const languageItems = $derived(LOCALE_OPTIONS.map(({ code, label }) => ({
    value: code,
    label,
    href: swapLocale(path, code),
  })));
</script>

{#snippet navigation()}
  <SiteNavLink href={u.assistants(lang)} active={path.includes("/assistants")}>{tr("nav_assistants", lang)}</SiteNavLink>
  <SiteNavLink href={u.services(lang)} active={path.includes("/services")}>{tr("nav_services", lang)}</SiteNavLink>
  <SiteNavLink href={u.creators(lang)} active={path.includes("/creators")}>{tr("nav_creators", lang)}</SiteNavLink>
  <SiteNavLink href={u.security(lang)} active={path.includes("/security")}>{tr("nav_security", lang)}</SiteNavLink>
  <SiteNavLink href="https://docs.shimpz.com" target="_blank" rel="noopener noreferrer">{tr("nav_docs", lang)} <span aria-hidden="true">↗</span></SiteNavLink>
{/snippet}

{#snippet actions()}
  <ActionLink href={u.install(lang)} variant="primary" size="compact">{tr("nav_install", lang)}</ActionLink>
  <AccountMenu {lang} />
  <DropdownMenu
    items={languageItems}
    value={lang}
    ariaLabel={`${tr("language", lang)}: ${currentLanguage}`}
    menuLabel={tr("language", lang)}
    triggerLabel={lang.toUpperCase()}
  />
{/snippet}

<PublicSiteHeader
  brandHref={u.home(lang)}
  brandAriaLabel="Shimpz home"
  navigationLabel={tr("nav_main", lang)}
  skipLabel={tr("skip_content", lang)}
  {navigation}
  {actions}
/>
