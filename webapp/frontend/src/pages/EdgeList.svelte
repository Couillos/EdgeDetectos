<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { num, pct, verdictBadge } from '../lib/format.js'
  import { startAnalysis } from '../lib/tasks.js'
  import { edgeSearch, edgeStatus, edgeSymbol, edgeSortBy, edgeSortDir, edgePage, selectedEdges } from '../lib/stores.js'
  import DataTable from '../components/DataTable.svelte'
  import VerdictBadge from '../components/VerdictBadge.svelte'

  const PER_PAGE = 50

  let symbols = $state([])
  let allEdges = $state([])
  let loading = $state(false)
  let error = $state('')
  let debounce = null

  // Reactive local copies from stores
  let search   = $state($edgeSearch)
  let status   = $state($edgeStatus)
  let symbol   = $state($edgeSymbol)
  let sortCol  = $state($edgeSortBy)
  let sortDir  = $state($edgeSortDir)
  let page     = $state($edgePage)
  let selected = $state($selectedEdges)

  // Sort & page in client
  let sorted = $derived.by(() => [...allEdges].sort((a, b) => {
    const av = a[sortCol], bv = b[sortCol]
    if (typeof av === 'string' || typeof bv === 'string') {
      const as_ = (av || '').toLowerCase(), bs = (bv || '').toLowerCase()
      return sortDir === 'asc' ? as_.localeCompare(bs) : bs.localeCompare(as_)
    }
    const fallback = sortDir === 'asc' ? 999999 : -999999
    return sortDir === 'asc' ? (av ?? fallback) - (bv ?? fallback) : (bv ?? fallback) - (av ?? fallback)
  }))
  let totalPages = $derived(Math.ceil(sorted.length / PER_PAGE))
  let paged = $derived(sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE))

  const columns = [
    {
      key: 'name', label: 'Name', sortable: true,
      render: (row) => `<a class="link link-hover truncate block max-w-xs" href="#/edges/${encodeURIComponent(row.name)}">${row.name}</a>`,
    },
    {
      key: 'signal_type', label: 'Type', sortable: true,
      render: null, // handled via extraRow
    },
    {
      key: 'verdict', label: 'Verdict', sortable: true,
    },
    { key: 'best_sharpe',  label: 'Sharpe',   numeric: true, sortable: true, format: v => num(v) },
    { key: 'best_winrate', label: 'Win Rate',  numeric: true, sortable: true, format: v => pct(v) },
    { key: 'total_signals',label: 'Signals',   numeric: true, sortable: true, format: v => v ?? '—' },
  ]

  function rowClass(row) {
    return selected.has(row.name) ? 'selected' : ''
  }

  onMount(async () => {
    try {
      symbols = await api.get('/api/symbols')
    } catch {}
    loadEdges()
  })

  async function loadEdges() {
    loading = true; error = ''
    try {
      const params = new URLSearchParams({ search, status, per_page: '200' })
      if (symbol) params.set('symbol', symbol)
      const data = await api.get('/api/edges?' + params)
      allEdges = data.edges || []
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
    // persist
    edgeSearch.set(search); edgeStatus.set(status); edgeSymbol.set(symbol)
    edgeSortBy.set(sortCol); edgeSortDir.set(sortDir); edgePage.set(page)
  }

  function onSearchInput(e) {
    clearTimeout(debounce)
    debounce = setTimeout(() => { search = e.target.value; page = 1; loadEdges() }, 300)
  }

  function onSymbolChange(e)  { symbol = e.target.value; page = 1; loadEdges() }
  function onStatusChange(e)  { status = e.target.value; page = 1; loadEdges() }
  function onSortChange(col, dir) { sortCol = col; sortDir = dir; edgeSortBy.set(col); edgeSortDir.set(dir) }

  function analyzeSelected() {
    startAnalysis(Array.from(selected), false, false, null, null, () => loadEdges())
  }
</script>

<svelte:head><title>Edges — Edge Generator</title></svelte:head>

<h1 class="text-xl font-semibold mb-4">Edges</h1>

<!-- Action bar (selected) -->
{#if selected.size > 0}
  <div class="mb-3 flex items-center gap-3">
    <button class="btn btn-primary btn-sm" onclick={analyzeSelected}>
      Analyze Selected ({selected.size})
    </button>
    <button class="btn btn-ghost btn-sm" onclick={() => { selected = new Set(); selectedEdges.set(new Set()) }}>
      Clear selection
    </button>
  </div>
{/if}

<!-- Toolbar -->
<div class="toolbar">
  <input
    class="input input-bordered input-sm flex-1 max-w-xs"
    placeholder="Search edges…"
    value={search}
    oninput={onSearchInput}
  />
  <select class="select select-bordered select-sm" value={symbol} onchange={onSymbolChange}>
    <option value="">All Symbols</option>
    {#each symbols as sym}<option value={sym}>{sym}</option>{/each}
  </select>
  <select class="select select-bordered select-sm" value={status} onchange={onStatusChange}>
    <option value="all">All</option>
    <option value="analyzed">Analyzed</option>
    <option value="pending">Pending</option>
  </select>
</div>

{#if loading}
  <div class="flex justify-center py-10"><span class="loading loading-spinner loading-md"></span></div>
{:else if error}
  <div class="alert alert-error text-sm">{error}</div>
{:else}
  <!-- Table (custom render for special columns) -->
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th class="w-10 text-center">
            <input type="checkbox" class="checkbox checkbox-xs"
              checked={paged.length > 0 && paged.every(r => selected.has(r.name))}
              onchange={(e) => {
                const s = new Set(selected)
                if (e.target.checked) paged.forEach(r => s.add(r.name))
                else paged.forEach(r => s.delete(r.name))
                selected = s; selectedEdges.set(s)
              }}
            />
          </th>
          {#each ['Name','Type','Verdict','Sharpe','Win Rate','Signals','Actions'] as label, i}
            {@const keys = ['name','signal_type','verdict','best_sharpe','best_winrate','total_signals',null]}
            {@const k = keys[i]}
            <th
              class:sorted={sortCol === k}
              class:num={i >= 3 && i < 6}
              class:cursor-pointer={!!k}
              onclick={() => k && onSortChange(k, sortCol === k ? (sortDir === 'asc' ? 'desc' : 'asc') : 'asc')}
            >
              {label}{sortCol === k ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#if paged.length === 0}
          <tr><td colspan="8"><div class="empty-state"><h3>No edges found</h3></div></td></tr>
        {:else}
          {#each paged as row (row.name)}
            <tr class:selected={selected.has(row.name)}>
              <td class="w-10 text-center">
                <input type="checkbox" class="checkbox checkbox-xs"
                  checked={selected.has(row.name)}
                  onchange={() => {
                    const s = new Set(selected)
                    s.has(row.name) ? s.delete(row.name) : s.add(row.name)
                    selected = s; selectedEdges.set(s)
                  }}
                />
              </td>
              <td>
                <a class="link link-hover truncate block max-w-xs text-sm"
                  href="#/edges/{encodeURIComponent(row.name)}">{row.name}</a>
              </td>
              <td>
                <span class="badge badge-sm {row.signal_type === 'long' ? 'badge-success' : row.signal_type === 'short' ? 'badge-error' : 'badge-info'}">
                  {(row.signal_type || 'BOTH').toUpperCase()}
                </span>
              </td>
              <td>
                {#if row.verdict}
                  <span class="badge badge-sm {verdictBadge(row.verdict)}">{row.verdict}</span>
                {:else}—{/if}
              </td>
              <td class="num">{row.best_sharpe != null ? num(row.best_sharpe) : '—'}</td>
              <td class="num">{row.best_winrate != null ? pct(row.best_winrate) : '—'}</td>
              <td class="num">{row.total_signals ?? '—'}</td>
              <td class="flex gap-1 items-center">
                <button class="btn btn-xs" onclick={() => push(`/edges/${encodeURIComponent(row.name)}`)}>View</button>
                {#if !row.has_analysis}
                  <button class="btn btn-xs btn-primary"
                    onclick={() => startAnalysis([row.name], false, false, null, null, () => loadEdges())}>Run</button>
                {/if}
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>

  <!-- Pagination -->
  {#if totalPages > 1}
    <div class="flex items-center justify-center gap-1 mt-4">
      <button class="btn btn-xs" disabled={page <= 1} onclick={() => { page--; edgePage.set(page) }}>Prev</button>
      {#each Array.from({length: Math.min(5, totalPages)}, (_, i) => Math.max(1, page - 2) + i).filter(p => p <= totalPages) as p}
        <button class="btn btn-xs {p === page ? 'btn-primary' : ''}" onclick={() => { page = p; edgePage.set(p) }}>{p}</button>
      {/each}
      <button class="btn btn-xs" disabled={page >= totalPages} onclick={() => { page++; edgePage.set(page) }}>Next</button>
      <span class="text-xs opacity-60 ml-2">{page}/{totalPages} ({sorted.length} total)</span>
    </div>
  {/if}
{/if}
