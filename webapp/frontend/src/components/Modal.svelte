<script>
  let { open = $bindable(false), title = '', onclose = null } = $props()
  let { children, actions } = $props()

  function close() {
    open = false
    onclose?.()
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="modal modal-open" onclick={(e) => e.target === e.currentTarget && close()}>
    <div class="modal-box">
      {#if title}
        <h3 class="font-bold text-lg mb-3">{title}</h3>
      {/if}
      {@render children?.()}
      <div class="modal-action">
        {@render actions?.()}
      </div>
    </div>
  </div>
{/if}
