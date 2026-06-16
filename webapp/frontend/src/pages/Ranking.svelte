<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { num, pct, verdictBadge, VERDICTS } from '../lib/format.js'
  import { rankFilters, rankSort, rankingSymbol } from '../lib/stores.js'
  import FilterBar from '../components/FilterBar.svelte'

  let symbols = $state([])
  let allEdges = $state([])
  let loading = $state(false)
  let error = $state('')

  let localFilters = $state({ ...$rankFilters })
  let localSort    = $state({ ...$rankSort })
  let symbol       = $state($rankingSymbol)

  const FILTER_SPEC = [
    { key: 'name',    label: 'Name',    type: 'text' },
    { key: 'verdict', label: 'Verdict', type: 'select', options: VERDICTS },
    { key: 'score',   label: 'Score',   type: 'range' },
    { key: 'sharpe',  label: 'Sharpe',  type: 'range' },
    { key: 'winrate', label: 'WinRate', type: 'range' },
    { key: 'tr',      label: 'TotRet',  type: 'range' },
    { key: 'sig',     label: 'Sig',     type: 'range' },
    { key: 'breadth', label: 'Breadth', type: 'range' },
    { key: 'tp',      label: 't-p',     type: 'range' },
    { key: 'mcp',     label: 'MC p',    type: 'range' },
    { key: 'ksp',     label: 'KS p',    type: 'range' },
  ]

  // Apply filters reactively
  let filtered = $derived.by(() => allEdges.filter(e => {
    const f = localFilters
    if (f.name && !e.name.toLowerCase().includes(f.name)) return false
    if (f.verdict && e.verdict !== f.verdict) return false
    if (f.scoreMin  !== '' && (e.score  ?? 0)    < +f.scoreMin)  return false
    if (f.scoreMax  !== '' && (e.score  ?? 0)    > +f.scoreMax)  return false
    if (f.sharpeMin !== '' && (e.sharpe ?? -999) < +f.sharpeMin) return false
    if (f.sharpeMax !== '' && (e.sharpe ?? 999)  > +f.sharpeMax) return false
    if (f.winrateMin!== '' && (e.winrate?? 0)    < +f.winrateMin)return false
    if (f.winrateMax!== '' && (e.winrate?? 100)  > +f.winrateMax)return false
    if (f.trMin     !== '' && (e.total_return??-1e9) < +f.trMin) return false
    if (f.trMax     !== '' && (e.total_return??1e9)  > +f.trMax) return false
    if (f.sigMin    !== '' && (e.sig    ?? 0)    < +f.sigMin)    return false
    if (f.sigMax    !== '' && (e.sig    ?? 999)  > +f.sigMax)    return false
    if (f.breadthMin!== '' && (e.breadth?? 0)    < +f.breadthMin)return false
    if (f.breadthMax!== '' && (e.breadth?? 999)  > +f.breadthMax)return false
    if (f.tpMin     !== '' && (e.t_p    ?? -1)   < +f.tpMin)    return false
    if (f.tpMax     !== '' && (e.t_p    ?? 2)    > +f.tpMax)    return false
    if (f.mcpMin    !== '' && (e.mc_p   ?? -1)   < +f.mcpMin)   return false
    if (f.mcpMax    !== '' && (e.mc_p   ?? 2)    > +f.mcpMax)   return false
    if (f.kspMin    !== '' && (e.ks_p   ?? -1)   < +f.kspMin)   return false
    if (f.kspMax    !== '' && (e.ks_p   ?? 2)    > +f.kspMax)   return false
    return true
  }))

  let sorted = $derived.by(() => [...filtered].sort((a, b) => {
    const c = localSort.col
    if (!c || c === '#') return 0
    const av = a[c], bv = b[c]
    if (typeof av === 'string') return localSort.dir === 'asc' ? (av||'').localeCompare(bv||'') : (bv||'').localeCompare(av||'')
    return localSort.dir === 'asc' ? (av||0)-(bv||0) : (bv||0)-(av||0)
  }))

  const COLS = [
    ['#',null], ['Name','name'], ['Verdict','verdict'], ['Score','score'],
    ['Sig','sig'], ['Breadth','breadth'], ['Sharpe','sharpe'], ['Win Rate','winrate'],
    ['Total Return','total_return'], ['t-p','t_p'], ['MC p','mc_p'], ['KS p','ks_p'],
  ]

  function toggleSort(key) {
    if (!key) return
    const dir = localSort.col === key ? (localSort.dir === 'asc' ? 'desc' : 'asc') : 'desc'
    localSort = { col: key, dir }
    rankSort.set(localSort)
  }

  function verdictRowCls(v) {
    return v ? `row-${v}` : ''
  }

  onMount(async () => {
    try { symbols = await api.get('/api/symbols') } catch {}
    loadRanking()
  })

  async function loadRanking() {
    loading = true; error = ''
    try {
      const data = await api.get(`/api/ranking?symbol=${encodeURIComponent(symbol)}`)
      allEdges = data.edges || []
      rankFilters.set(localFilters)
      rankingSymbol.set(symbol)
    } catch(e) { error = e.message }
    finally { loading = false }
  }

  $effect(() => { rankFilters.set(localFilters) })
</script>

<svelte:head><title>Ranking — Edge Generator</title></svelte:head>

<h1 class="text-xl font-semibold mb-4">Ranking</h1>

<div class="toolbar">
  <select class="select select-bordered select-sm" value={symbol} onchange={(e) => { symbol = e.target.value; rankingSymbol.set(symbol); loadRanking() }}>
    {#each symbols as sym}<option value={sym}>{sym}</option>{/each}
  </select>
  <span class="text-xs opacity-60">{sorted.length} edges (of {allEdges.length})</span>
</div>

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
              class:num={i >= 3}
              class:cursor-pointer={!!key}
              onclick={() => toggleSort(key)}
            >
              {label}{localSort.col === key ? (localSort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each sorted as e, i}
          <tr class="{verdictRowCls(e.verdict)} cursor-pointer" onclick={() => push(`/edges/${encodeURIComponent(e.name)}`)}>
            <td>{i+1}</td>
            <td class="max-w-xs truncate text-sm">{e.name}</td>
            <td>
              {#if e.verdict}
                <span class="badge badge-sm {verdictBadge(e.verdict)}">{e.verdict}</span>
              {:else}—{/if}
            </td>
            <td class="num">{num(e.score)}</td>
            <td class="num">{e.sig ?? '-'}</td>
            <td class="num">{e.breadth ?? '-'}</td>
            <td class="num">{num(e.sharpe)}</td>
            <td class="num">{pct(e.winrate)}</td>
            <td class="num">{num(e.total_return, 2)}</td>
            <td class="num text-xs">{e.t_p != null ? e.t_p.toFixed(3) : '-'}</td>
            <td class="num text-xs">{e.mc_p != null ? e.mc_p.toFixed(3) : '-'}</td>
            <td class="num text-xs">{e.ks_p != null ? e.ks_p.toFixed(3) : '-'}</td>
          </tr>
        {:else}
          <tr><td colspan="12"><div class="empty-state"><h3>No edges match the filters</h3></div></td></tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}
