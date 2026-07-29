<script lang="ts">
  import { SERVICES, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import Seo from "$lib/components/Seo.svelte";
  import ServiceCard from "$lib/components/ServiceCard.svelte";
  import PageIntro from "$lib/components/PageIntro.svelte";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
</script>

<Seo title={`${tr("services_title", lang)} · Shimpz`} description={tr("services_lead", lang)} {lang} />

<section class="wrap pt-10" aria-labelledby="services-title">
  <PageIntro
    headingId="services-title"
    title={tr("services_title", lang)}
    description={tr("services_lead", lang)} />

  <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {#each SERVICES as service (service.id)}<ServiceCard {service} {lang} />{/each}
  </div>
</section>
