<script lang="ts">
  import type { Locale } from "$lib/catalog";
  import InstitutionalPage from "$lib/components/InstitutionalPage.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { institutionalPage } from "$lib/institutional";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutionalPage("security", lang));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />
<InstitutionalPage {content} />
