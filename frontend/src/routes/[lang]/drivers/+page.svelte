<script lang="ts">
  import { DRIVERS, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Seo from "$lib/components/Seo.svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import DriverCard from "$lib/components/DriverCard.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
</script>

<Seo title={`${tr("drivers_title", lang)} · Shimpz`} description={tr("drivers_lead", lang)} {lang} />

<section class="wrap pt-10">
  <Breadcrumbs items={[{ label: tr("home", lang), href: u.home(lang) }, { label: tr("nav_drivers", lang) }]} />
  <h1 class="text-3xl font-bold">{tr("drivers_title", lang)}</h1>
  <p class="mt-3 max-w-2xl dim">{tr("drivers_lead", lang)}</p>

  <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {#each DRIVERS as driver (driver.id)}<DriverCard {driver} {lang} />{/each}
  </div>
</section>
