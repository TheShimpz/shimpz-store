<script lang="ts">
  import { t, creatorOf, type Locale, type Service } from "$lib/catalog";
  import { tr } from "$lib/i18n";
  import { u } from "$lib/url";
  import ServiceIcon from "./ServiceIcon.svelte";
  import CreatorTag from "./CreatorTag.svelte";

  let { service, lang }: { service: Service; lang: Locale } = $props();
</script>

<div class="card relative flex flex-col">
  <a href={u.service(lang, service)} class="absolute inset-0" aria-label={service.name}></a>
  <div class="flex items-start gap-4">
    <ServiceIcon icon={service.icon} size={52} brand={service.brand} />
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <span class="truncate text-[15px] font-semibold">{service.name}</span>
        <span class="badge">{service.category}</span>
      </div>
      <p class="mt-1 line-clamp-2 text-sm dim">{t(service.summary, lang)}</p>
      <div class="relative z-10 mt-2 w-fit"><CreatorTag handle={creatorOf(service)} {lang} /></div>
    </div>
  </div>
  <p class="mt-auto pt-4 text-xs dim">{service.features.length} {tr("capabilities", lang)}</p>
</div>
