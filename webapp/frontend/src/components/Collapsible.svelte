<script>
  import { untrack } from 'svelte'
  let { title = '', defaultOpen = false, children } = $props()
  let open = $state(untrack(() => defaultOpen))
</script>

<div>
  <button
    class="collapsible-trigger text-base font-semibold mb-3 w-full text-left"
    onclick={() => (open = !open)}
    type="button"
  >
    <span class="chevron" class:open>{open ? '▼' : '▶'}</span>
    {title}
  </button>
  {#if open}
    {@render children?.()}
  {/if}
</div>
