<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { dashboardSymbols } from '../lib/stores.js'
  import { startAnalysis } from '../lib/tasks.js'

  let symbols = $state([])
  let total = $state(0), analyzed = $state(0), pending = $state(0)
  let loading = $state(true), error = $state('')
  let maxCores = $state(4)
  let workers = $state(3)
  let lastEdge = $state(null)

  // Local binding for the multi-select (keeps store in sync)
  let selectedSymbols = $state([])

  $effect(() => {
    selectedSymbols = $dashboardSymbols
  })

  onMount(load)

  async function load() {
    loading = true; error = ''
    try {
      const [syms, cpuData] = await Promise.all([
        api.get('/api/symbols'),
        api.get('/api/cpu-cores').catch(() => ({ cores: 4 })),
      ])
      symbols = syms
      maxCores = cpuData.cores
      workers = Math.max(1, maxCores - 1)

      if ($dashboardSymbols.length === 0) {
        dashboardSymbols.set([...syms])
      }
      selectedSymbols = $dashboardSymbols

      await loadStats()
    } catch (e) { error = e.message }
    finally { loading = false }
  }

  async function loadStats() {
    const sel = selectedSymbols.length > 0 ? selectedSymbols : symbols
    const results = await Promise.all(sel.map(sym => Promise.all([
      api.get(`/api/edges?per_page=1&status=all&symbol=${encodeURIComponent(sym)}`),
      api.get(`/api/edges?per_page=1&status=analyzed&symbol=${encodeURIComponent(sym)}`),
    ])))
    total = 0; analyzed = 0
    for (const [all, ana] of results) {
      total += all.total || 0
      analyzed += ana.total || 0
    }
    pending = total - analyzed
    lastEdge = results[0]?.[1]?.edges?.[0] ?? null
  }

  function onSymbolChange(e) {
    const opts = Array.from(e.target.selectedOptions).map(o => o.value)
    let sel
    if (opts.includes('__all__') || opts.length === 0 || opts.length === symbols.length) {
      sel = [...symbols]
    } else {
      sel = opts.filter(s => s !== '__all__')
    }
    dashboardSymbols.set(sel)
    selectedSymbols = sel
    loadStats()
  }

  function analyzeAll() {
    startAnalysis(null, true, false, selectedSymbols, workers)
  }
</script>

{#if loading}
  <div class="flex justify-center p-16"><span class="loading loading-spinner loading-lg"></span></div>
{:else if error}
  <div class="empty-state"><h3>Error loading dashboard</h3><p class="text-sm">{error}</p></div>
{:else}
  <!-- Symbol selector -->
  <div class="mb-4">
    <label for="symbols-select" class="label label-text text-xs uppercase tracking-wide opacity-60 mb-1 block">Symbols to analyze</label>
    <select
      id="symbols-select"
      multiple
      class="select select-bordered w-full max-w-xs"
      style="min-height:80px"
      onchange={onSymbolChange}
    >
      <option value="__all__" selected={selectedSymbols.length === symbols.length}>All Symbols</option>
      {#each symbols as sym}
        <option value={sym} selected={selectedSymbols.includes(sym)}>{sym}</option>
      {/each}
    </select>
  </div>

  <!-- KPI cards -->
  <div class="card bg-base-300 border border-base-content/10 mb-4">
    <div class="card-body py-3 px-2">
      <div class="kpi-group">
        <div class="kpi-item"><div class="kpi-value">{total}</div><div class="kpi-label">Total</div></div>
        <div class="kpi-item"><div class="kpi-value text-success">{analyzed}</div><div class="kpi-label">Analyzed</div></div>
        <div class="kpi-item"><div class="kpi-value text-warning">{pending}</div><div class="kpi-label">Pending</div></div>
        <div class="kpi-item"><div class="kpi-value text-primary">{symbols.length}</div><div class="kpi-label">Symbols</div></div>
      </div>
    </div>
  </div>

  <!-- Actions -->
  <div class="flex items-center gap-3 flex-wrap mb-6">
    <label for="workers-input" class="text-xs opacity-60">Workers:</label>
    <input
      id="workers-input"
      type="number" min="1" max={maxCores}
      bind:value={workers}
      class="input input-sm input-bordered w-16"
    />
    <button class="btn btn-primary btn-sm gap-2" onclick={analyzeAll}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      Analyze All
    </button>
    <button class="btn btn-sm" onclick={() => push('/ranking')}>View Ranking</button>
    <button class="btn btn-sm" onclick={() => push('/oos')}>OOS Validation</button>
  </div>

  <!-- Last analysis -->
  {#if lastEdge}
    <div class="card bg-base-300 border border-base-content/10">
      <div class="card-body py-3">
        <div class="text-xs opacity-60 mb-1">Last Analysis</div>
        <div class="text-sm">{lastEdge.name}</div>
        <div class="flex gap-2 items-center mt-1">
          {#if lastEdge.verdict}
            <span class="badge badge-sm">{lastEdge.verdict}</span>
          {/if}
          {#if lastEdge.best_sharpe != null}
            <span class="text-xs opacity-60">Sharpe: {lastEdge.best_sharpe?.toFixed(2)}</span>
          {/if}
        </div>
      </div>
    </div>
  {/if}
{/if}

<svelte:head><title>Dashboard — Edge Generator</title></svelte:head>
