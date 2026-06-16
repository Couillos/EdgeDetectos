<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { num, pct, verdictBadge } from '../lib/format.js'
  import { detailSymbol } from '../lib/stores.js'
  import { startAnalysis } from '../lib/tasks.js'
  import Collapsible from '../components/Collapsible.svelte'
  import CodeBlock from '../components/CodeBlock.svelte'

  // svelte-spa-router passes matched params via this prop
  let { params = {} } = $props()

  let edgeName  = $derived(decodeURIComponent(params.name || ''))
  let symbols   = $state([])
  let edge      = $state(null)
  let sourceCode= $state('')
  let loading   = $state(false)
  let error     = $state('')
  let symbol    = $state($detailSymbol)
  let lightboxSrc = $state('')
  let oosData   = $state(null)

  // Reload whenever edgeName changes (navigation between edges)
  $effect(() => {
    if (edgeName) load()
  })

  // Load OOS JSON when report PNG is absent
  $effect(() => {
    if (edge?.oos_report_json && !edge?.oos_report_png) {
      api.get(edge.oos_report_json + `?symbol=${encodeURIComponent(symbol)}`)
        .then(d => (oosData = d)).catch(() => (oosData = null))
    } else {
      oosData = null
    }
  })

  async function load() {
    loading = true; error = ''; edge = null; oosData = null
    try {
      const [e, syms] = await Promise.all([
        api.get(`/api/edges/${encodeURIComponent(edgeName)}?symbol=${encodeURIComponent(symbol)}`),
        api.get('/api/symbols'),
      ])
      edge = e
      symbols = syms
      loadSource()
    } catch(e) { error = e.message }
    finally { loading = false }
  }

  async function loadSource() {
    try {
      const d = await api.get(`/api/edge-source/${encodeURIComponent(edgeName)}`)
      sourceCode = d.source || ''
    } catch { sourceCode = '' }
  }

  function onSymbolChange(e) {
    symbol = e.target.value
    detailSymbol.set(symbol)
    load()
  }

  function rerun() {
    startAnalysis([edgeName], true, false, [symbol], null, () => load())
  }

  function openLightbox(src) { lightboxSrc = src }
  function closeLightbox()   { lightboxSrc = '' }
</script>

<svelte:head><title>{edgeName} — Edge Generator</title></svelte:head>

{#if loading}
  <div class="flex justify-center p-16"><span class="loading loading-spinner loading-lg"></span></div>
{:else if error}
  <div class="empty-state"><h3>Error loading edge</h3><p class="text-sm">{error}</p></div>
{:else if edge}
  <!-- Header -->
  <div class="detail-header">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div class="flex-1 min-w-0">
        <h1 class="truncate">{edge.signal_name || edgeName}</h1>
        {#if edge.description}
          <p class="text-sm opacity-60 mt-1">{edge.description}</p>
        {/if}
      </div>
      <select class="select select-bordered select-sm" value={symbol} onchange={onSymbolChange}>
        {#each symbols as sym}<option value={sym}>{sym}</option>{/each}
      </select>
    </div>

    <div class="detail-meta">
      {#if edge.verdict}
        <span class="badge {verdictBadge(edge.verdict)}">
          {edge.verdict}
        </span>
      {/if}
      {#if edge.best_horizon}  <span class="text-sm opacity-60">Best: {edge.best_horizon}</span> {/if}
      {#if edge.total_signals != null} <span class="text-sm opacity-60">{edge.total_signals} signals</span> {/if}
      {#if edge.source_file}   <span class="text-xs opacity-40">{edge.source_file.split('/').pop()}</span> {/if}
    </div>

    <div class="detail-actions">
      <button class="btn btn-primary btn-sm" onclick={rerun}>Re-run Analysis</button>
      <button class="btn btn-sm" onclick={() => push('/ranking')}>View Ranking</button>
    </div>
  </div>

  <!-- Analysis Reports: IS + OOS side by side -->
  {#if edge.report_png || edge.oos_report_png}
    <div class="detail-section">
      <h2>Analysis Report</h2>
      <div class="grid grid-cols-2 gap-4">
        <!-- In-Sample -->
        <div>
          <h3 class="text-sm opacity-60 mb-2">In-Sample</h3>
          {#if edge.report_png}
            {@const imgSrc = edge.report_png + `?symbol=${encodeURIComponent(symbol)}`}
            <button type="button" class="w-full p-0 border-0 bg-transparent cursor-zoom-in" onclick={() => openLightbox(imgSrc)} aria-label="Open IS report fullscreen">
              <img src={imgSrc} alt="IS report"
                class="w-full rounded-lg border border-base-content/10"
                onerror={(e) => { e.target.style.display='none'; e.target.nextElementSibling?.classList.remove('hidden') }}
              />
            </button>
            <p class="hidden text-sm opacity-60 text-center py-4">IS report image not available</p>
          {:else}
            <p class="text-sm opacity-60 text-center py-4">Not yet analyzed</p>
          {/if}
        </div>

        <!-- Out-of-Sample -->
        <div>
          <h3 class="text-sm opacity-60 mb-2">Out-of-Sample</h3>
          {#if edge.oos_report_png}
            {@const imgSrc = edge.oos_report_png + `?symbol=${encodeURIComponent(symbol)}`}
            <button type="button" class="w-full p-0 border-0 bg-transparent cursor-zoom-in" onclick={() => openLightbox(imgSrc)} aria-label="Open OOS report fullscreen">
              <img src={imgSrc} alt="OOS report"
                class="w-full rounded-lg border border-base-content/10"
                onerror={(e) => { e.target.style.display='none'; e.target.nextElementSibling?.classList.remove('hidden') }}
              />
            </button>
            <p class="hidden text-sm opacity-60 text-center py-4">OOS report image not available</p>
          {:else}
            <p class="text-sm opacity-60 text-center py-4">Run OOS validation to generate this report.</p>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <!-- Horizon stats table (always shown when analysis exists) -->
  {#if edge.horizons && Object.keys(edge.horizons).length > 0}
    <div class="detail-section">
      <h2>Horizon Stats</h2>
      <div class="table-wrap">
        <table class="data-table horizon-table">
          <thead>
            <tr>
              <th>Horizon</th>
              <th class="num">Signals</th><th class="num">Mean %</th><th class="num">Win Rate</th>
              <th class="num">Sharpe</th><th class="num">t-p</th><th class="num">MC p</th><th class="num">Return %</th>
            </tr>
          </thead>
          <tbody>
            {#each Object.entries(edge.horizons).sort((a,b) => +a[0] - +b[0]) as [h, d]}
              <tr class:best={String(edge.best_horizon_num) === h}>
                <td style="font-weight:{String(edge.best_horizon_num)===h?600:400}">+{h}h</td>
                <td class="num">{d.n_signals}</td>
                <td class="num">{num((d.mean ?? 0) * 100)}</td>
                <td class="num">{pct(d.winrate)}</td>
                <td class="num">{num(d.sharpe)}</td>
                <td class="num">{num(d.t_p, 4)}</td>
                <td class="num">{num(d.mc_p, 4)}</td>
                <td class="num">{num(d.total_return, 2)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  <!-- Source code -->
  <div class="detail-section">
    <Collapsible title="Source Code">
      {#if sourceCode}
        <CodeBlock code={sourceCode} />
      {:else}
        <p class="text-sm opacity-60">Source file not available.</p>
      {/if}
    </Collapsible>
  </div>

  <!-- Persistence -->
  {#if edge.persistence}
    {@const p = edge.persistence}
    <div class="detail-section">
      <h2>Persistence</h2>
      <div class="flex gap-3 flex-wrap">
        <div class="card bg-base-300 border border-base-content/10">
          <div class="card-body py-3 px-4">
            <div class="text-lg font-bold">{p.rolling_windows_positive_pct?.toFixed(1)}%</div>
            <div class="text-xs opacity-60 uppercase tracking-wide">Windows Positive</div>
          </div>
        </div>
        <div class="card bg-base-300 border border-base-content/10">
          <div class="card-body py-3 px-4">
            <div class="text-lg font-bold">{p.years_positive}/{p.years_total}</div>
            <div class="text-xs opacity-60 uppercase tracking-wide">Years Positive</div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Statistical tests -->
  {#if edge.tests}
    {@const t = edge.tests}
    <div class="detail-section">
      <h2>Statistical Tests</h2>
      <div class="flex gap-3 flex-wrap">
        <div class="card bg-base-300 border border-base-content/10">
          <div class="card-body py-3 px-4">
            <div class="text-lg font-bold">{t.tests_significant ?? 0}</div>
            <div class="text-xs opacity-60 uppercase tracking-wide">Tests Significant</div>
          </div>
        </div>
        {#if t.best_t_test_p != null}
          <div class="card bg-base-300 border border-base-content/10">
            <div class="card-body py-3 px-4">
              <div class="text-lg font-bold">{num(t.best_t_test_p, 4)}</div>
              <div class="text-xs opacity-60 uppercase tracking-wide">Best t-test p</div>
            </div>
          </div>
        {/if}
        {#if t.best_mc_p != null}
          <div class="card bg-base-300 border border-base-content/10">
            <div class="card-body py-3 px-4">
              <div class="text-lg font-bold">{num(t.best_mc_p, 4)}</div>
              <div class="text-xs opacity-60 uppercase tracking-wide">Best MC p</div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Raw JSON -->
  <div class="detail-section">
    <Collapsible title="Raw JSON">
      <pre class="raw-json">{JSON.stringify(edge, null, 2)}</pre>
    </Collapsible>
  </div>
{/if}

<!-- Lightbox -->
{#if lightboxSrc}
  <div class="lightbox-overlay" role="dialog" aria-modal="true" aria-label="Report fullscreen">
    <button type="button" class="lightbox-backdrop" onclick={closeLightbox} aria-label="Close lightbox"></button>
    <img src={lightboxSrc} alt="Report (full size)" />
  </div>
{/if}
