<script lang="ts">
  import "@shimpz/frontend/theme.css";
  import "../app.css";
  let { children } = $props();
</script>

<div class="shimpz-theme">{@render children()}</div>
