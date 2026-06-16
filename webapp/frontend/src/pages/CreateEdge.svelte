<script>
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { api } from '../lib/api.js'
  import { addToast } from '../lib/stores.js'

  let name = $state('')
  let longFormula = $state('')
  let shortFormula = $state('')
  let horizons = $state('1,4,6,12,24,48,72,168')
  let description = $state('')
  let errorMsg = $state('')
  let submitting = $state(false)
  let showModal = $state(false)
  let createdName = $state('')
  let showIndicators = $state(true)
  let indicators = $state({})

  onMount(async () => {
    try {
      const d = await api.get('/api/indicators')
      indicators = d.categories || {}
    } catch {}
  })

  async function handleCreate(e) {
    e.preventDefault()
    errorMsg = ''
    if (!name.trim() || !longFormula.trim()) {
      errorMsg = 'Name and Long Formula are required'
      return
    }
    submitting = true
    try {
      await api.post('/api/edges/create', {
        name: name.trim(),
        long_formula: longFormula.trim(),
        short_formula: shortFormula.trim(),
        horizons,
        description: description.trim(),
      })
      createdName = name.trim()
      showModal = true
    } catch (e) {
      errorMsg = e.message
    } finally {
      submitting = false
    }
  }
</script>

<svelte:head><title>Create Edge — Edge Generator</title></svelte:head>

<h1 class="text-xl font-semibold mb-4">Create Edge</h1>

<form class="card bg-base-300 border border-base-content/10 max-w-2xl" onsubmit={handleCreate}>
  <div class="card-body gap-4">

    <div class="form-control">
      <label for="ce-name" class="label label-text font-semibold uppercase text-xs tracking-wide">Name *</label>
      <input id="ce-name" class="input input-bordered" bind:value={name} placeholder="e.g. RSI 14 oversold <25" required />
    </div>

    <div class="form-control">
      <label for="ce-long" class="label label-text font-semibold uppercase text-xs tracking-wide">Long Formula *</label>
      <textarea id="ce-long" class="textarea textarea-bordered font-mono text-sm" rows="3" bind:value={longFormula}
        placeholder="e.g. rsi(close, 14) < 25" required></textarea>
      <div class="label label-text-alt opacity-60">Use: rsi(close,14), sma(close,20), bb_lower(close,20,2), close > ema(close,50)</div>
    </div>

    <div class="form-control">
      <label for="ce-short" class="label label-text font-semibold uppercase text-xs tracking-wide">Short Formula</label>
      <textarea id="ce-short" class="textarea textarea-bordered font-mono text-sm" rows="3" bind:value={shortFormula}
        placeholder="e.g. rsi(close, 14) > 75 — optional"></textarea>
      <div class="label label-text-alt opacity-60">Optional — leave empty for long-only edges</div>
    </div>

    <div class="form-control">
      <label for="ce-horizons" class="label label-text font-semibold uppercase text-xs tracking-wide">Horizons</label>
      <input id="ce-horizons" class="input input-bordered font-mono" bind:value={horizons} />
      <div class="label label-text-alt opacity-60">Comma-separated list of hour horizons</div>
    </div>

    <div class="form-control">
      <label for="ce-desc" class="label label-text font-semibold uppercase text-xs tracking-wide">Description</label>
      <textarea id="ce-desc" class="textarea textarea-bordered" rows="2" bind:value={description}
        placeholder="Describe the edge logic…"></textarea>
    </div>

    <!-- Indicator reference -->
    <div>
      <button type="button" class="btn btn-link btn-sm px-0 text-primary"
        onclick={() => (showIndicators = !showIndicators)}>
        {showIndicators ? '▼' : '▶'} Indicator reference
      </button>
      {#if showIndicators && Object.keys(indicators).length > 0}
        <div class="mt-2 p-3 bg-base-200 rounded-lg max-h-72 overflow-y-auto columns-3 gap-4 text-sm">
          {#each Object.entries(indicators) as [cat, names]}
            <div class="break-inside-avoid mb-3">
              <strong class="text-primary text-xs">{cat}</strong><br />
              {#each names as n}
                <code class="text-xs opacity-70 mr-1">{n}</code>
              {/each}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    {#if errorMsg}
      <div class="alert alert-error text-sm py-2">{errorMsg}</div>
    {/if}

    <div class="card-actions">
      <button type="submit" class="btn btn-success" disabled={submitting}>
        {submitting ? 'Creating…' : 'Create & Validate'}
      </button>
    </div>
  </div>
</form>

<!-- Success modal -->
{#if showModal}
  <div class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg mb-2">Edge Created</h3>
      <p class="text-sm opacity-70 mb-4">"{createdName}" has been created successfully.</p>
      <div class="modal-action">
        <button class="btn btn-primary" onclick={() => { showModal = false; push(`/edges/${encodeURIComponent(createdName)}`) }}>View Edge</button>
        <button class="btn" onclick={() => (showModal = false)}>Close</button>
      </div>
    </div>
  </div>
{/if}
