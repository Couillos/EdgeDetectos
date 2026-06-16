<!--
  Generic filter bar.

  Props:
    spec   — Array<{key, label, type: 'text'|'select'|'range', options?}>
             'range' generates two inputs: `${key}Min` and `${key}Max`
    filters — $bindable object containing all filter values
-->
<script>
  let { spec = [], filters = $bindable({}) } = $props()
</script>

<div class="filter-bar">
  {#each spec as f}
    <div class="filter-group">
      <label for="{f.key}-ctrl">{f.label}</label>
      {#if f.type === 'text'}
        <input
          id="{f.key}-ctrl"
          class="filter-input"
          placeholder="{f.label}…"
          value={filters[f.key] ?? ''}
          oninput={(e) => (filters = { ...filters, [f.key]: e.target.value.toLowerCase() })}
        />
      {:else if f.type === 'select'}
        <select
          id="{f.key}-ctrl"
          class="filter-input filter-select select select-xs"
          value={filters[f.key] ?? ''}
          onchange={(e) => (filters = { ...filters, [f.key]: e.target.value })}
        >
          {#each f.options as opt}
            <option value={opt}>{opt || 'All'}</option>
          {/each}
        </select>
      {:else if f.type === 'range'}
        <input
          id="{f.key}-ctrl"
          class="filter-input"
          aria-label="{f.label} min"
          placeholder="Min"
          value={filters[`${f.key}Min`] ?? ''}
          oninput={(e) => (filters = { ...filters, [`${f.key}Min`]: e.target.value })}
        />
        <input
          class="filter-input"
          aria-label="{f.label} max"
          placeholder="Max"
          value={filters[`${f.key}Max`] ?? ''}
          oninput={(e) => (filters = { ...filters, [`${f.key}Max`]: e.target.value })}
        />
      {/if}
    </div>
  {/each}
</div>
