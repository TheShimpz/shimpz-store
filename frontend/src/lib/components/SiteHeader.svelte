<script lang="ts">
  import { afterNavigate } from "$app/navigation";
  import { ActionLink, DropdownMenu, SiteHeader as PublicSiteHeader } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
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
  <span data-header-navigation-empty hidden></span>
{/snippet}

{#snippet githubIcon()}
  <svg viewBox="0 0 24 24">
    <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.88c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.35 1.09 2.92.83.09-.65.35-1.09.64-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.6 9.6 0 0 1 12 6.82a9.6 9.6 0 0 1 2.5.34c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" />
  </svg>
{/snippet}

{#snippet actions()}
  <ActionLink
    class="github-link"
    href="https://github.com/TheShimpz"
    target="_blank"
    rel="noopener noreferrer"
    variant="primary"
    size="lg"
    icon={githubIcon}
    glitch
  >
    GitHub
  </ActionLink>
  <div class="language-switch" data-sveltekit-noscroll onclickcapture={rememberLanguageScroll}>
    <DropdownMenu
      items={languageItems}
      value={lang}
      ariaLabel={`${tr("language", lang)}: ${currentLanguage}`}
      menuLabel={tr("language", lang)}
      triggerLabel={lang.toUpperCase()}
      glitch
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
  :global(.github-link svg) { width: 1rem; height: 1rem; fill: currentColor; }
  :global([data-slot="site-header"].shimpz-site-header) { background: transparent; }
  :global([data-slot="site-header"] nav:has([data-header-navigation-empty])) { display: none; }
  @media (min-width: 961px) {
    :global([data-slot="site-header"] [data-slot="site-header-actions"]) { grid-column: 3; }
  }
  :global([data-slot="site-header"] [data-slot="shimpz-brand-mark"]) {
    margin-inline: 1.125rem;
    transform: scale(2);
    animation: symbol-glitch 4.8s 210ms infinite steps(1, end);
  }
  :global([data-slot="site-header"] [data-slot="shimpz-brand-wordmark"]) { font-size: 1.84rem; }
  @keyframes symbol-glitch {
    0%, 86%, 91%, 100% { transform: translate(0) scale(2); filter: none; }
    87% { transform: translate(-2px, 1px) scale(2); filter: drop-shadow(2px 0 var(--color-magenta)); }
    88% { transform: translate(2px, -1px) scale(2); filter: drop-shadow(-2px 0 var(--color-cyan)); }
    89% { transform: translate(-1px, 0) scale(2); filter: drop-shadow(1px 0 var(--color-magenta)); }
  }
  @media (prefers-reduced-motion: reduce) {
    :global([data-slot="site-header"] [data-slot="shimpz-brand-mark"]) { animation: none; }
  }
</style>
