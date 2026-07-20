<script lang="ts">
  let {
    variant = "compact",
    product = "",
    href = "/",
    ariaLabel = "Shimpz home",
    asset = "/brand/shimpz-cyberchimp.png",
  }: {
    variant?: "compact" | "hero";
    product?: string;
    href?: string;
    ariaLabel?: string;
    asset?: string;
  } = $props();
</script>

<a class:hero={variant === "hero"} class="brand-lockup" {href} aria-label={ariaLabel}>
  <img src={asset} alt="" aria-hidden="true" width="1254" height="1254" />
  <span class="brand-type">
    <span class="wordmark">Shimpz</span>
    {#if product}<span class="product">{product}</span>{/if}
  </span>
</a>

<style>
  .brand-lockup {
    display: inline-flex;
    min-width: 0;
    align-items: center;
    gap: 0.72rem;
    color: var(--color-fg);
    text-decoration: none;
  }

  img {
    width: 2.8rem;
    height: 2.8rem;
    flex: none;
    mix-blend-mode: screen;
    object-fit: contain;
  }

  .brand-type {
    display: flex;
    min-width: 0;
    align-items: baseline;
    gap: 0.65rem;
  }

  .wordmark {
    font-family: var(--font-mono);
    font-size: 1.28rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.055em;
  }

  .product {
    color: var(--color-muted-2);
    font-family: var(--font-mono);
    font-size: 0.62rem;
    font-weight: 600;
    line-height: 1;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .hero {
    gap: clamp(1rem, 3vw, 1.8rem);
    pointer-events: none;
  }

  .hero img {
    width: clamp(7rem, 16vw, 10rem);
    height: clamp(7rem, 16vw, 10rem);
  }

  .hero .brand-type {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.6rem;
  }

  .hero .wordmark {
    font-size: clamp(2.5rem, 6vw, 4.4rem);
    letter-spacing: -0.075em;
  }

  .hero .product {
    color: var(--color-cyan);
    font-size: clamp(0.66rem, 1.4vw, 0.8rem);
    letter-spacing: 0.24em;
  }

  @media (max-width: 520px) {
    .brand-lockup:not(.hero) .product {
      display: none;
    }

    .hero {
      align-items: center;
      flex-direction: column;
      text-align: center;
    }

    .hero .brand-type {
      align-items: center;
    }
  }
</style>
