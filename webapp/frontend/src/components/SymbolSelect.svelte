<script>
  import { api } from '../lib/api.js'
  import { onMount } from 'svelte'

  let { value = $bindable('BTC/USDT'), onchange = null } = $props()
  let symbols = $state([])

  onMount(async () => {
    try { symbols = await api.get('/api/symbols') } catch {}
  })

  function handleChange(e) {
    value = e.target.value
    onchange?.(value)
  }
</script>

<select class="select select-sm select-bordered" {value} onchange={handleChange}>
  {#each symbols as sym}
    <option value={sym} selected={sym === value}>{sym}</option>
  {/each}
</select>
