<script lang="ts">
  import { t, type Driver, type App, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import AppCard from "$lib/components/AppCard.svelte";
  import Icon from "$lib/components/Icon.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const driver = $derived(data.driver as Driver);
  const apps = $derived(data.apps as App[]);
</script>

<Seo title={`${driver.name} · Shimpz drivers`} description={t(driver.summary, lang)} {lang} />

<section class="wrap pt-10">
  <Breadcrumbs items={[{ label: tr("home", lang), href: u.home(lang) }, { label: tr("nav_drivers", lang), href: u.drivers(lang) }, { label: driver.name }]} />

  <div class="flex items-center gap-5">
    <Icon glyph={driver.icon} id={driver.id} size={80} brand={driver.brand} />
    <div>
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-3xl font-bold tracking-tight">{driver.name}</h1>
        <span class="badge">{driver.category}</span>
      </div>
      <p class="mt-1.5 text-lg dim">{t(driver.summary, lang)}</p>
    </div>
  </div>

  <div class="mt-10 grid gap-8 lg:grid-cols-[1fr_320px]">
    <div class="space-y-10">
      <div>
        <h2 class="kicker">{tr("what_it_does", lang)}</h2>
        <p class="mt-3 max-w-2xl text-lg leading-relaxed">{t(driver.blurb, lang)}</p>
      </div>
      {#if apps.length}
        <div>
          <h2 class="kicker">{tr("used_by", lang)}</h2>
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            {#each apps as app (app.id)}<AppCard {app} {lang} />{/each}
          </div>
        </div>
      {/if}
    </div>

    <aside class="lg:sticky lg:top-24 lg:self-start">
      <div class="panel">
        <h2 class="kicker">{tr("grants_title", lang)}</h2>
        <ul class="mt-4 space-y-3 text-sm">
          {#each driver.grants as g (g.en)}
            <li class="flex gap-2"><span style="color:var(--color-primary)">✓</span><span>{t(g, lang)}</span></li>
          {/each}
        </ul>
      </div>
    </aside>
  </div>
</section>
