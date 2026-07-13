<script lang="ts">
  import { t, appsUsingDriver, type Driver, type Locale } from "$lib/catalog";
  import { u } from "$lib/url";
  import Icon from "./Icon.svelte";

  let { driver, lang }: { driver: Driver; lang: Locale } = $props();
  const count = $derived(appsUsingDriver(driver.id).length);
</script>

<a class="card" href={u.driver(lang, driver)}>
  <div class="flex items-start gap-4">
    <Icon glyph={driver.icon} id={driver.id} size={52} brand={driver.brand} />
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <span class="truncate text-[15px] font-semibold">{driver.name}</span>
        <span class="badge">{driver.category}</span>
      </div>
      <p class="mt-1 line-clamp-2 text-sm dim">{t(driver.summary, lang)}</p>
    </div>
  </div>
  <p class="mt-4 text-xs dim">{count} {count === 1 ? "app" : "apps"}</p>
</a>
