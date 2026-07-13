<script lang="ts">
  import { APPS, usedCategories, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import AppCard from "$lib/components/AppCard.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
</script>

<Seo title={`${tr("all_apps", lang)} · Shimpz`} description={tr("apps_lead", lang)} {lang} />

<section class="wrap pt-10">
  <Breadcrumbs items={[{ label: tr("home", lang), href: u.home(lang) }, { label: tr("nav_apps", lang) }]} />
  <h1 class="text-3xl font-bold">{tr("all_apps", lang)}</h1>
  <p class="mt-3 max-w-2xl dim">{tr("apps_lead", lang)}</p>

  <div class="mt-6 flex flex-wrap gap-2">
    <span class="chip is-active">{tr("all_apps", lang)}</span>
    {#each usedCategories() as cat (cat)}<a class="chip" href={u.category(lang, cat)}>{cat}</a>{/each}
  </div>

  <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {#each APPS as app (app.id)}<AppCard {app} {lang} />{/each}
  </div>
</section>
