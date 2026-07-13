<script lang="ts">
  import { t, DRIVER_BY_ID, APP_BY_ID, relatedApps, type App, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import AppCard from "$lib/components/AppCard.svelte";
  import Icon from "$lib/components/Icon.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const app = $derived(data.app as App);
  const perms = $derived(app.permissions.map((id) => DRIVER_BY_ID.get(id)).filter(Boolean));
  const deps = $derived(app.dependsOn.map((id) => APP_BY_ID.get(id)).filter(Boolean));

  let msg = $state("");
  async function install() {
    const cap = localStorage.getItem("shimpz_current_capsule");
    const me = await (await fetch("/api/me")).json().catch(() => ({}));
    if (!me.authenticated || !cap) {
      // need a Shimpz account (the P4 gate) + a selected Capsule — send them to the Capsules console
      window.location.href = u.capsule(lang);
      return;
    }
    msg = tr("requesting", lang);
    try {
      const r = await fetch(`/api/capsules/${cap}/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app: app.id }),
      });
      msg = r.ok ? "✓ " + tr("install_ok", lang) : "✗ " + tr("install_err", lang);
    } catch {
      msg = "✗ " + tr("install_err", lang);
    }
  }
</script>

<Seo title={`${app.name} · Shimpz`} description={t(app.tagline, lang)} {lang} />

<section class="wrap pt-10">
  <Breadcrumbs
    items={[
      { label: tr("home", lang), href: u.home(lang) },
      { label: tr("nav_apps", lang), href: u.apps(lang) },
      { label: app.category, href: u.category(lang, app.category) },
      { label: app.name },
    ]}
  />

  <div class="flex items-center gap-5">
    <Icon glyph={app.icon} id={app.id} size={80} />
    <div>
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-3xl font-bold tracking-tight">{app.name}</h1>
        <span class="badge badge-price">{t(app.price, lang)}</span>
      </div>
      <p class="mt-1.5 text-lg dim">{t(app.tagline, lang)}</p>
    </div>
  </div>

  <div class="mt-12 grid gap-10 lg:grid-cols-[1fr_340px]">
    <div class="space-y-12">
      <div>
        <h2 class="kicker">{tr("what_it_does", lang)}</h2>
        <p class="mt-4 max-w-2xl text-lg leading-relaxed">{t(app.spec, lang)}</p>
      </div>

      <div>
        <h2 class="kicker">{tr("permissions", lang)}</h2>
        <p class="mt-1.5 text-sm dim">{tr("permissions_hint", lang)}</p>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          {#each perms as d (d!.id)}
            <a class="perm" href={u.driver(lang, d!)}>
              <Icon glyph={d!.icon} id={d!.id} size={38} brand={d!.brand} />
              <span class="min-w-0">
                <span class="block font-medium">{d!.name}</span>
                <span class="block truncate text-sm dim">{t(d!.summary, lang)}</span>
              </span>
            </a>
          {/each}
        </div>
      </div>

      <div>
        <h2 class="kicker">{tr("depends_on", lang)}</h2>
        <p class="mt-1.5 text-sm dim">{tr("depends_hint", lang)}</p>
        {#if deps.length}
          <div class="mt-4 space-y-3">
            {#each deps as dep (dep!.id)}
              <a class="perm !justify-between" href={u.app(lang, dep!)}>
                <span class="flex items-center gap-3"><Icon glyph={dep!.icon} id={dep!.id} size={38} /><span class="font-medium">{dep!.name}</span></span>
                <span class="text-sm dim">{dep!.category} →</span>
              </a>
            {/each}
          </div>
        {:else}
          <p class="mt-4 text-sm dim">{tr("no_deps", lang)}</p>
        {/if}
      </div>
    </div>

    <aside class="lg:sticky lg:top-24 lg:self-start">
      <div class="panel space-y-4">
        <div class="flex items-center justify-between text-sm"><span class="dim">{tr("category", lang)}</span><a class="transition hover:text-[var(--color-primary)]" href={u.category(lang, app.category)}>{app.category}</a></div>
        <div class="flex items-center justify-between text-sm"><span class="dim">{tr("publisher", lang)}</span><span>{app.publisher}</span></div>
        <div class="flex items-center justify-between text-sm"><span class="dim">{tr("price", lang)}</span><span>{t(app.price, lang)}</span></div>
        <div class="border-t hair pt-4">
          {#if app.available}
            <button class="btn-primary w-full" onclick={install}>{tr("install", lang)}</button>
            <p class="mt-3 text-xs dim">{tr("runs_at", lang)} <code class="rounded bg-[var(--color-elevated)] px-1.5 py-0.5">{app.id}.grid.shimpz.com</code></p>
            {#if msg}<p class="mt-2 text-sm">{msg}</p>{/if}
          {:else}
            <div class="btn-ghost w-full cursor-default justify-center opacity-70">{tr("coming_soon", lang)}</div>
          {/if}
        </div>
      </div>
    </aside>
  </div>

  {#if relatedApps(app).length}
    <div class="mt-16">
      <h2 class="mb-5 text-xl font-semibold tracking-tight">{tr("related", lang)}</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {#each relatedApps(app) as r (r.id)}<AppCard app={r} {lang} />{/each}
      </div>
    </div>
  {/if}
</section>
