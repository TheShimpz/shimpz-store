<script lang="ts">
  import type { Locale } from "$lib/catalog";
  import { swapLocale, u } from "$lib/url";

  let { lang }: { lang: Locale } = $props();
  const copy = $derived(lang === "pt"
    ? { assistants: "Assistants", teams: "Times", how: "Como funciona", login: "Entrar", nav: "Navegação principal", language: "Idioma" }
    : { assistants: "Assistants", teams: "Teams", how: "How it works", login: "Sign in", nav: "Main navigation", language: "Language" });
</script>

<a class="skip-link" href="#main-content">{lang === "pt" ? "Pular para o conteúdo" : "Skip to content"}</a>

<header class="home-header">
  <div class="wrap header-inner">
    <a class="brand" href={u.home(lang)} aria-label="Shimpz home"><span aria-hidden="true">S</span><strong>Shimpz</strong></a>

    <nav aria-label={copy.nav}>
      <a href="#assistants">{copy.assistants}</a>
      <a href="#teams">{copy.teams}</a>
      <a href="#how-it-works">{copy.how}</a>
      <a class="sign-in" href={u.login(lang)}>{copy.login}</a>
    </nav>

    <div class="locale" aria-label={copy.language}>
      <a href={swapLocale(`/${lang}`, "en")} class:active={lang === "en"} aria-current={lang === "en" ? "page" : undefined}>EN</a>
      <a href={swapLocale(`/${lang}`, "pt")} class:active={lang === "pt"} aria-current={lang === "pt" ? "page" : undefined}>PT</a>
    </div>
  </div>
</header>

<style>
  .skip-link {
    position: fixed;
    z-index: 100;
    top: 0.75rem;
    left: 1rem;
    padding: 0.65rem 0.9rem;
    background: var(--color-fg);
    color: var(--color-bg);
    font-weight: 700;
    transform: translateY(-180%);
  }

  .skip-link:focus { transform: translateY(0); }

  .home-header {
    position: sticky;
    z-index: 50;
    top: 0;
    box-shadow: 0 1px 0 color-mix(in oklab, var(--color-border) 75%, transparent);
    background: color-mix(in oklab, var(--color-bg) 88%, transparent);
    backdrop-filter: blur(18px);
  }

  .header-inner {
    display: grid;
    min-height: 4.75rem;
    grid-template-columns: 1fr auto auto;
    align-items: center;
    gap: clamp(1rem, 3vw, 2.5rem);
  }

  .brand {
    display: inline-flex;
    justify-self: start;
    align-items: center;
    gap: 0.65rem;
    color: var(--color-fg);
    font-family: var(--font-mono);
  }

  .brand span {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    background: linear-gradient(135deg, var(--color-cyan), var(--color-magenta));
    color: var(--color-accent-ink);
    font-size: 0.82rem;
    font-weight: 800;
    clip-path: polygon(22% 0, 78% 0, 100% 22%, 100% 78%, 78% 100%, 22% 100%, 0 78%, 0 22%);
  }

  .brand strong { font-size: 0.92rem; letter-spacing: -0.04em; }

  nav { display: flex; align-items: center; gap: clamp(0.3rem, 1vw, 1.2rem); }

  nav a {
    padding: 0.6rem 0.45rem;
    color: var(--color-muted);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  nav a:hover { color: var(--color-fg); }
  nav .sign-in {
    padding-inline: 0.8rem;
    background: #000;
    box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--color-cyan) 48%, var(--color-border-strong));
    color: var(--color-cyan);
    clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  }

  .locale {
    display: flex;
    align-items: center;
    padding: 0.2rem;
    background: #000;
    box-shadow: inset 0 0 0 1px var(--color-border-strong);
    clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  }

  .locale a {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    color: var(--color-muted);
    font-family: var(--font-mono);
    font-size: 0.62rem;
    font-weight: 700;
  }

  .locale a.active { background: linear-gradient(135deg, var(--color-cyan), var(--color-magenta)); color: var(--color-accent-ink); clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }

  @media (max-width: 760px) {
    .header-inner { grid-template-columns: 1fr auto; }
    nav {
      grid-row: 2;
      grid-column: 1 / -1;
      justify-content: space-between;
      overflow-x: auto;
      border-top: 1px solid var(--color-border);
      scrollbar-width: none;
    }
    nav::-webkit-scrollbar { display: none; }
  }

  @media (max-width: 420px) {
    nav a { padding-inline: 0.25rem; font-size: 0.78rem; }
  }
</style>
