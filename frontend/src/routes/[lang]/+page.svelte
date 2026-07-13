<script lang="ts">
  import { usedCategories, appsInCategory, DRIVERS, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import AppCard from "$lib/components/AppCard.svelte";
  import DriverCard from "$lib/components/DriverCard.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
</script>

<Seo title={tr("home_title", lang)} description={tr("home_desc", lang)} {lang} />

<section class="wrap pt-16 pb-8 sm:pt-28">
  <span class="badge" style="border-color:color-mix(in oklab, var(--color-primary) 30%, var(--color-border))">
    <span class="mr-1.5 inline-block size-1.5 rounded-full" style="background:var(--color-primary)"></span>
    Shimpz · {tr("brand_tag", lang)}
  </span>
  <h1 class="mt-6 max-w-4xl text-5xl font-extrabold leading-[1.04] tracking-tight sm:text-7xl">
    {tr("hero_h1_a", lang)} <span class="gradient-text">{tr("hero_h1_b", lang)}</span> {tr("hero_h1_c", lang)}
  </h1>
  <p class="mt-6 max-w-2xl text-lg leading-relaxed dim sm:text-xl">{tr("hero_p", lang)}</p>
  <div class="mt-9 flex flex-wrap gap-3">
    <a href={u.capsule(lang)} class="btn-primary">{tr("create_capsule", lang)} →</a>
    <a href={u.apps(lang)} class="btn-ghost">{tr("browse_apps", lang)}</a>
    <a href={u.drivers(lang)} class="btn-ghost">{tr("explore_drivers", lang)}</a>
  </div>
</section>

{#each usedCategories() as cat (cat)}
  <section class="wrap mt-14">
    <div class="mb-4 flex items-end justify-between">
      <h2 class="text-xl font-semibold">{cat}</h2>
      <a href={u.category(lang, cat)} class="text-sm dim transition hover:text-[var(--color-fg)]">{tr("all_apps", lang)} →</a>
    </div>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each appsInCategory(cat) as app (app.id)}<AppCard {app} {lang} />{/each}
    </div>
  </section>
{/each}

<section class="wrap mt-16">
  <div class="mb-4 flex items-end justify-between">
    <h2 class="text-xl font-semibold">{tr("nav_drivers", lang)}</h2>
    <a href={u.drivers(lang)} class="text-sm dim transition hover:text-[var(--color-fg)]">{tr("explore_drivers", lang)} →</a>
  </div>
  <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    {#each DRIVERS.slice(0, 4) as driver (driver.id)}<DriverCard {driver} {lang} />{/each}
  </div>
</section>
