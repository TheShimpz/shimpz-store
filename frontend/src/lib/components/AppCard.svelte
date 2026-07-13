<script lang="ts">
  import { t, DRIVER_BY_ID, type App, type Locale } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import Icon from "./Icon.svelte";

  let { app, lang }: { app: App; lang: Locale } = $props();
  const perms = $derived(app.permissions.map((id) => DRIVER_BY_ID.get(id)).filter(Boolean));
</script>

<a class="card group" href={u.app(lang, app)}>
  <div class="flex items-start gap-4">
    <Icon glyph={app.icon} id={app.id} size={52} />
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <span class="truncate text-[15px] font-semibold">{app.name}</span>
        {#if !app.available}<span class="badge">{tr("coming_soon", lang)}</span>{/if}
      </div>
      <p class="mt-1 line-clamp-2 text-sm dim">{t(app.tagline, lang)}</p>
    </div>
  </div>
  <div class="mt-4 flex items-center justify-between">
    <div class="flex items-center -space-x-1.5">
      {#each perms.slice(0, 5) as d (d!.id)}
        <span class="grid size-6 place-items-center rounded-md border text-xs hair" style="background:var(--color-elevated)" title={d!.name}>{d!.icon}</span>
      {/each}
      {#if perms.length > 5}<span class="pl-3 text-xs dim">+{perms.length - 5}</span>{/if}
    </div>
    <span class="badge badge-price">{t(app.price, lang)}</span>
  </div>
</a>
