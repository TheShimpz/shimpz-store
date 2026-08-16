<script lang="ts">
  import type { Locale } from "$lib/locales";
  import { ActionLink } from "@shimpz/frontend";
  import InstitutionalPage from "$lib/components/InstitutionalPage.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { institutionalPage } from "$lib/institutional";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutionalPage("openSource", lang));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />
<InstitutionalPage {content} />
<div class="wrap action"><ActionLink href="https://github.com/TheShimpz" target="_blank" rel="noopener noreferrer" variant="primary">GitHub ↗</ActionLink></div>

<style>.action { padding-block-end: clamp(4rem,8vw,7rem); }</style>
