<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { num, pct, verdictBadge, VERDICTS } from '../lib/format.js'
  import { oosFilters, oosSort, oosSymbol } from '../lib/stores.js'
  import { startOOS } from '../lib/tasks.js'
  import FilterBar from '../components/FilterBar.svelte'

  let symbols = $state([])
  let allEdges = $state([])
  let verdicts = $state({})
  let loading = $state(false)
  let error = $state('')
  let maxCores = $state(4)
  let workers = $state(3)

  let symbol       = $state($oosSymbol)
  let localFilters = $state({ ...$oosFilters })
  let localSort    = $state({ ...$oosSort })

  const FILTER_SPEC = [
    { key: 'name',     label: 'Name',      type: 'text' },
    { key: 'verdict',  label: 'Verdict',   type: 'select', options: VERDICTS },
    { key: 'isSc',     label: 'IS Score',  type: 'range' },
    { key: 'oosSc',    label: 'OOS Score', type: 'range' },
    { key: 'finalSc',  label: 'Final Sc',  type: 'range' },
    { key: 'dec',      label: 'Decay',     type: 'range' },
    { key: 'isSh',     label: 'IS Sharpe', type: 'range' },
    { key: 'oosSh',    label: 'OOS Sharpe',type: 'range' },
    { key: 'oosWr',    label: 'OOS WR',    type: 'range' },
    { key: 'oosTp',    label: 'OOS t-p',   type: 'range' },
    { key: 'oosMcp',   label: 'OOS MC p',  type: 'range' },
    { key: 'distKsp',  label: 'Dist KS p', type: 'range' },
  ]

  let filtered = $derived.by(() => allEdges.filter(e => {
    const f = localFilters
    if (f.name     && !e.name.toLowerCase().includes(f.name)) return false
    if (f.verdict  && e.verdict !== f.verdict) return false
    if (f.isScMin  !== '' && (e.is_score    ??0)   < +f.isScMin)  return false
    if (f.isScMax  !== '' && (e.is_score    ??100) > +f.isScMax)  return false
    if (f.oosScMin !== '' && (e.oos_score   ??0)   < +f.oosScMin) return false
    if (f.oosScMax !== '' && (e.oos_score   ??100) > +f.oosScMax) return false
    if (f.finalScMin!==''&& (e.final_score  ??0)   < +f.finalScMin)return false
    if (f.finalScMax!==''&& (e.final_score  ??100) > +f.finalScMax)return false
    if (f.decMin   !== '' && (e.decay       ??-1)  < +f.decMin)   return false
    if (f.decMax   !== '' && (e.decay       ??2)   > +f.decMax)   return false
    if (f.isShMin  !== '' && (e.is_sharpe   ??-999)< +f.isShMin)  return false
    if (f.isShMax  !== '' && (e.is_sharpe   ??999) > +f.isShMax)  return false
    if (f.oosShMin !== '' && (e.oos_sharpe  ??-999)< +f.oosShMin) return false
    if (f.oosShMax !== '' && (e.oos_sharpe  ??999) > +f.oosShMax) return false
    if (f.oosWrMin !== '' && (e.oos_winrate ??0)   < +f.oosWrMin) return false
    if (f.oosWrMax !== '' && (e.oos_winrate ??100) > +f.oosWrMax) return false
    if (f.oosTpMin !== '' && (e.oos_t_p     ??-1)  < +f.oosTpMin) return false
    if (f.oosTpMax !== '' && (e.oos_t_p     ??2)   > +f.oosTpMax) return false
    if (f.oosMcpMin!==''&& (e.oos_mc_p     ??-1)  < +f.oosMcpMin)return false
    if (f.oosMcpMax!==''&& (e.oos_mc_p     ??2)   > +f.oosMcpMax)return false
    if (f.distKspMin!==''&& (e.dist_ks_p   ??-1)  < +f.distKspMin)return false
    if (f.distKspMax!==''&& (e.dist_ks_p   ??2)   > +f.distKspMax)return false
    return true
  }))

  let sorted = $derived.by(() => [...filtered].sort((a, b) => {
    const c = localSort.col
    if (!c) return 0
    const av = a[c], bv = b[c]
    if (typeof av === 'string') return localSort.dir === 'asc' ? (av||'').localeCompare(bv||'') : (bv||'').localeCompare(av||'')
    return localSort.dir === 'asc' ? (av||0)-(bv||0) : (bv||0)-(av||0)
  }))

  const COLS = [
    ['Name','name'],['Verdict','verdict'],['IS Score','is_score'],['OOS Score','oos_score'],
    ['Final Score','final_score'],['Decay','decay'],['IS Sharpe','is_sharpe'],
    ['OOS Sharpe','oos_sharpe'],['OOS WR','oos_winrate'],['OOS t-p','oos_t_p'],
    ['OOS MC p','oos_mc_p'],['Dist KS p','dist_ks_p'],
  ]

  function toggleSort(key) {
    const dir = localSort.col === key ? (localSort.dir === 'asc' ? 'desc' : 'asc') : 'desc'
    localSort = { col: key, dir }; oosSort.set(localSort)
  }
  function rowCls(v) {
    return v ? `row-${v}` : ''
  }

  onMount(async () => {
    try {
      symbols = await api.get('/api/symbols')
      const cpu = await api.get('/api/cpu-cores').catch(() => ({ cores: 4 }))
      maxCores = cpu.cores; workers = Math.max(1, maxCores - 1)
    } catch {}
    loadOOS()
  })

  async function loadOOS() {
    loading = true; error = ''
    try {
      const data = await api.get(`/api/oos/${encodeURIComponent(symbol)}`)
      allEdges = data.edges || []
      verdicts = data.verdicts || {}
      oosSymbol.set(symbol)
      oosFilters.set(localFilters)
    } catch(e) { error = e.message }
    finally { loading = false }
  }

  $effect(() => { oosFilters.set(localFilters) })
</script>

<svelte:head><title>OOS Validation — Edge Generator</title></svelte:head>

<h1 class="text-xl font-semibold mb-4">OOS Validation</h1>

<div class="toolbar">
  <select class="select select-bordered select-sm" value={symbol}
    onchange={(e) => { symbol = e.target.value; oosSymbol.set(symbol); loadOOS() }}>
    {#each symbols as sym}<option value={sym}>{sym}</option>{/each}
  </select>
  <label for="oos-workers" class="text-xs opacity-60">Workers:</label>
  <input id="oos-workers" type="number" min="1" max={maxCores} bind:value={workers} class="input input-sm input-bordered w-16" />
  <button class="btn btn-primary btn-sm" onclick={() => startOOS(symbol, workers, () => loadOOS())}>
    Run OOS Validation
  </button>
  <span class="text-xs opacity-60">{sorted.length} edges (of {allEdges.length})</span>
</div>

<!-- Verdict summary -->
{#if allEdges.length > 0}
  <div class="card bg-base-300 border border-base-content/10 mb-4">
    <div class="card-body p-0">
      <div class="flex">
        <div class="oos-card strong"><div class="count">{verdicts.STRONG??0}</div><div class="label">STRONG</div></div>
        <div class="oos-card pass"><div class="count">{verdicts.MODERATE??0}</div><div class="label">MODERATE</div></div>
        <div class="oos-card weak"><div class="count">{verdicts.WEAK??0}</div><div class="label">WEAK</div></div>
        <div class="oos-card fail"><div class="count">{verdicts.NONE??0}</div><div class="label">NONE</div></div>
      </div>
    </div>
  </div>
{/if}

<FilterBar spec={FILTER_SPEC} bind:filters={localFilters} />

{#if loading}
  <div class="flex justify-center py-10"><span class="loading loading-spinner loading-md"></span></div>
{:else if error}
  <div class="alert alert-error text-sm">{error}</div>
{:else}
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          {#each COLS as [label, key], i}
            <th
              class:sorted={localSort.col === key}
              class:num={i >= 2}
              class:cursor-pointer={true}
              onclick={() => toggleSort(key)}
            >
              {label}{localSort.col === key ? (localSort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each sorted as e}
          <tr class="{rowCls(e.verdict)} cursor-pointer" onclick={() => push(`/edges/${encodeURIComponent(e.name)}`)}>
            <td class="text-sm truncate max-w-xs">{e.name}</td>
            <td>
              {#if e.verdict}
                <span class="badge badge-sm {verdictBadge(e.verdict)}">{e.verdict}</span>
              {:else}—{/if}
            </td>
            <td class="num">{num(e.is_score)}</td>
            <td class="num">{num(e.oos_score)}</td>
            <td class="num">{num(e.final_score)}</td>
            <td class="num" style="color:{(e.decay||0)>0.5?'var(--color-error)':'var(--color-success)'}">{pct((e.decay||0)*100)}</td>
            <td class="num">{num(e.is_sharpe)}</td>
            <td class="num">{num(e.oos_sharpe)}</td>
            <td class="num">{pct(e.oos_winrate)}</td>
            <td class="num text-xs">{e.oos_t_p!=null?e.oos_t_p.toFixed(3):'-'}</td>
            <td class="num text-xs">{e.oos_mc_p!=null?e.oos_mc_p.toFixed(3):'-'}</td>
            <td class="num text-xs">{e.dist_ks_p!=null?e.dist_ks_p.toFixed(3):'-'}</td>
          </tr>
        {:else}
          <tr><td colspan="12"><div class="empty-state"><h3>No OOS data — run validation first</h3></div></td></tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}
