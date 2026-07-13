<script lang="ts">
  import { page } from "$app/stores";
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u, swapLocale } from "$lib/url";

  let { data, children } = $props();
  const lang = $derived(data.lang as Locale);
  const path = $derived($page.url.pathname);
</script>

<header class="sticky top-0 z-10 border-b hair backdrop-blur" style="background:color-mix(in oklab, var(--color-bg) 82%, transparent)">
  <div class="wrap flex h-16 items-center gap-4">
    <a href={u.home(lang)} class="mono flex items-center gap-2.5 text-lg font-extrabold uppercase tracking-wide">
      <span class="app-icon grid place-items-center" style="--g1:#00f0ff;--g2:#ff2a6d;width:28px;height:28px;font-size:15px">◆</span>
      <span class="glitch" data-text="SHIMPZ" style="color:var(--color-fg)">SHIMPZ</span>
    </a>
    <span class="hidden text-sm dim sm:inline">· {tr("brand_tag", lang)}</span>
    <nav class="ml-auto flex items-center gap-1 text-sm">
      <a href={u.apps(lang)} class="rounded-lg px-3 py-1.5 transition hover:text-[var(--color-fg)]" class:text-[var(--color-fg)]={path.includes("/apps")} class:dim={!path.includes("/apps")}>{tr("nav_apps", lang)}</a>
      <a href={u.drivers(lang)} class="rounded-lg px-3 py-1.5 transition hover:text-[var(--color-fg)]" class:text-[var(--color-fg)]={path.includes("/drivers")} class:dim={!path.includes("/drivers")}>{tr("nav_drivers", lang)}</a>
      <div class="ml-2 flex items-center rounded-lg border hair p-0.5 text-xs">
        <a href={swapLocale(path, "en")} class="rounded-md px-2 py-1 transition" class:chip={false} style={lang === "en" ? "background:var(--color-primary);color:#04121a;font-weight:600" : "color:var(--color-muted)"}>EN</a>
        <a href={swapLocale(path, "pt")} class="rounded-md px-2 py-1 transition" style={lang === "pt" ? "background:var(--color-primary);color:#04121a;font-weight:600" : "color:var(--color-muted)"}>PT</a>
      </div>
    </nav>
  </div>
</header>

{@render children()}

<footer class="mt-24 border-t hair py-10">
  <div class="wrap flex flex-wrap items-center justify-between gap-4 text-sm dim">
    <span>Shimpz · {tr("footer", lang)}</span>
    <div class="flex gap-4">
      <a href={u.apps(lang)} class="transition hover:text-[var(--color-fg)]">{tr("nav_apps", lang)}</a>
      <a href={u.drivers(lang)} class="transition hover:text-[var(--color-fg)]">{tr("nav_drivers", lang)}</a>
      <a href="https://pay.shimpz.com" style="color:var(--color-primary)">ShimpzPay</a>
    </div>
  </div>
</footer>
