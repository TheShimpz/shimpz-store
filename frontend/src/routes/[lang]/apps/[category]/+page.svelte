<script lang="ts">
  import { usedCategories, type Locale, type AppCategory, type App } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import AppCard from "$lib/components/AppCard.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const category = $derived(data.category as AppCategory);
  const apps = $derived(data.apps as App[]);
</script>

<Seo title={`${category} apps · Shimpz`} description={`${category} apps for your Shimpz — ${tr("apps_lead", lang)}`} {lang} />

<section class="wrap pt-10">
  <Breadcrumbs items={[{ label: tr("home", lang), href: u.home(lang) }, { label: tr("nav_apps", lang), href: u.apps(lang) }, { label: category }]} />
  <h1 class="text-3xl font-bold">{category}</h1>

  <div class="mt-6 flex flex-wrap gap-2">
    <a class="chip" href={u.apps(lang)}>{tr("all_apps", lang)}</a>
    {#each usedCategories() as c (c)}
      <a class="chip" class:is-active={c === category} href={u.category(lang, c)}>{c}</a>
    {/each}
  </div>

  <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {#each apps as app (app.id)}<AppCard {app} {lang} />{/each}
  </div>
</section>
