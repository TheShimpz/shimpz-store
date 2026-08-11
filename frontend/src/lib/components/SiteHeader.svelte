<script lang="ts">
  import { afterNavigate } from "$app/navigation";
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
  const languageScrollKey = "shimpz:language-scroll-y";
  let restoreToken = 0;

  function rememberLanguageScroll(event: MouseEvent): void {
    if (
      event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ||
      !(event.target instanceof Element)
    ) return;
    const anchor = event.target.closest<HTMLAnchorElement>("a[href]");
    if (!anchor) return;
    try {
      window.sessionStorage.setItem(languageScrollKey, JSON.stringify({
        path: new URL(anchor.href).pathname,
        top: window.scrollY,
      }));
    } catch {
      // Navigation remains functional when per-tab storage is unavailable.
    }
  }

  afterNavigate((navigation) => {
    let saved: { path?: unknown; top?: unknown } | undefined;
    try {
      const raw = window.sessionStorage.getItem(languageScrollKey);
      window.sessionStorage.removeItem(languageScrollKey);
      if (raw !== null) saved = JSON.parse(raw);
    } catch {
      return;
    }
    if (
      navigation.type !== "link" || navigation.to?.url.pathname !== saved?.path ||
      typeof saved?.top !== "number" || !Number.isFinite(saved.top) || saved.top < 0
    ) return;
    const top = saved.top;

    const token = ++restoreToken;
    const cancellation = new AbortController();
    const cancel = () => {
      ++restoreToken;
      cancellation.abort();
    };
    for (const event of ["wheel", "touchstart", "pointerdown", "keydown"]) {
      window.addEventListener(event, cancel, { once: true, passive: true, signal: cancellation.signal });
    }
    let timeout = window.setTimeout(restore, 250);
    function restore(): void {
      window.clearTimeout(timeout);
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
        if (token !== restoreToken || cancellation.signal.aborted) return;
        window.scrollTo({ top, behavior: "instant" });
        cancellation.abort();
      }));
    }
    void document.fonts.ready.then(restore);
  });
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
  <div class="language-switch" data-sveltekit-noscroll onclickcapture={rememberLanguageScroll}>
    <DropdownMenu
      items={languageItems}
      value={lang}
      ariaLabel={`${tr("language", lang)}: ${currentLanguage}`}
      menuLabel={tr("language", lang)}
      triggerLabel={lang.toUpperCase()}
    />
  </div>
{/snippet}

<PublicSiteHeader
  brandHref={u.home(lang)}
  brandAriaLabel={tr("brand_home", lang)}
  contentWidth="editorial"
  navigationLabel={tr("nav_main", lang)}
  skipLabel={tr("skip_content", lang)}
  {navigation}
  {actions}
/>

<style>
  .language-switch { display: contents; }
</style>
