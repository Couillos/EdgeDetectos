<script>
  import { toasts } from '../lib/stores.js'
  let dying = $state(new Set())

  function dismiss(id) {
    dying = new Set([...dying, id])
    setTimeout(() => {
      toasts.update(list => list.filter(t => t.id !== id))
      dying = new Set([...dying].filter(x => x !== id))
    }, 500)
  }
</script>

<div class="toast-container">
  {#each $toasts as t (t.id)}
    <button
      type="button"
      class="toast-item {t.type}"
      class:out={dying.has(t.id)}
      onclick={() => dismiss(t.id)}
    >
      {t.msg}
    </button>
  {/each}
</div>

<style>
  button.toast-item { text-align: left; background: none; font: inherit; cursor: pointer; }
</style>
