<script lang="ts">
  import { ActionLink } from "@shimpz/frontend";
  import type { Locale } from "$lib/catalog";
  import InstallCommand from "$lib/components/InstallCommand.svelte";
  import InstitutionalPage from "$lib/components/InstitutionalPage.svelte";
  import Seo from "$lib/components/Seo.svelte";
  import { tr } from "$lib/i18n";
  import { institutionalPage } from "$lib/institutional";

  let { data } = $props();
  const lang = $derived(data.lang as Locale);
  const content = $derived(institutionalPage("install", lang));
</script>

<Seo title={content.seoTitle} description={content.seoDescription} {lang} />
<InstitutionalPage {content} />

<section class="wrap installer" aria-labelledby="installer-title">
  <p>Shimpz // Local</p>
  <h2 id="installer-title">{tr("install_shimpz", lang)}</h2>
  <InstallCommand {lang} />
  <div class="platforms">
    <ActionLink href="https://docs.shimpz.com/install/linux/" target="_blank" rel="noopener noreferrer">Linux ↗</ActionLink>
    <ActionLink href="https://docs.shimpz.com/install/macos/" target="_blank" rel="noopener noreferrer">macOS ↗</ActionLink>
    <ActionLink href="https://docs.shimpz.com/install/windows/" target="_blank" rel="noopener noreferrer">Windows ↗</ActionLink>
  </div>
</section>

<style>
  .installer { padding-block-end: clamp(5rem,10vw,9rem); }
  .installer > p { margin: 0 0 1rem; color: var(--color-cyan); font: 600 .68rem/1.4 var(--font-mono); letter-spacing: .15em; text-transform: uppercase; }
  h2 { margin: 0 0 2rem; font-size: clamp(2rem,4vw,3.6rem); letter-spacing: -.04em; }
  .platforms { display: flex; flex-wrap: wrap; gap: .75rem; margin-block-start: 1rem; }
</style>
