<script lang="ts">
  import { Button } from "@shimpz/frontend";

  const videoId = "M7lc1UVf-VE";
  let playing = $state(false);
</script>

{#snippet playIcon()}
  <span class="play-icon"></span>
{/snippet}

<div class="video-frame" data-slot="homepage-video">
  <div class="video-stage">
    {#if playing}
      <iframe
        src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`}
        title="YouTube embed placeholder"
        allow="autoplay; encrypted-media; picture-in-picture"
        allowfullscreen
      ></iframe>
    {:else}
      <div class="scanlines" aria-hidden="true"></div>
      <Button class="video-button" type="button" variant="secondary" size="xl" icon={playIcon} glitch aria-label="Play example video" onclick={() => playing = true}>
        PLAY // DEMO
      </Button>
      <span class="video-label" aria-hidden="true">YOUTUBE // PLACEHOLDER</span>
    {/if}
  </div>
</div>

<style>
  .video-frame {
    width: min(100%, 47rem);
    padding: 1px;
    background: linear-gradient(120deg, var(--color-cyan), var(--color-magenta));
    clip-path: polygon(0 0, calc(100% - 1.1rem) 0, 100% 1.1rem, 100% 100%, 1.1rem 100%, 0 calc(100% - 1.1rem));
  }
  .video-stage {
    position: relative;
    display: grid;
    aspect-ratio: 16 / 9;
    place-items: center;
    overflow: hidden;
    background: #02070a;
    clip-path: inherit;
  }
  iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }
  .scanlines {
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(to bottom, transparent 0 3px, rgb(0 229 255 / 0.07) 3px 4px);
    pointer-events: none;
  }
  :global(.video-button) {
    --shimpz-control-cut: 0.75rem;
    position: relative;
    z-index: 1;
  }
  .play-icon {
    width: 0;
    height: 0;
    border-block: 0.42rem solid transparent;
    border-inline-start: 0.7rem solid currentColor;
  }
  .video-label {
    position: absolute;
    inset-block-end: 0.8rem;
    inset-inline-start: 1rem;
    color: var(--color-muted);
    font: 600 0.58rem/1 var(--font-mono);
    letter-spacing: 0.14em;
  }
  @media (prefers-reduced-motion: reduce) {
    .scanlines { display: none; }
  }
</style>
