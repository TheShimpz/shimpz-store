<script lang="ts">
  import type { Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
</script>

<!-- Fallback content for clients that do not follow the prerendered permanent redirect. -->
<section class="wrap pt-10">
  <p class="dim">
    {tr("drivers_title", lang)}
    <a class="btn-ghost ml-3" href={u.services(lang)}>{tr("explore_drivers", lang)} →</a>
  </p>
</section>
