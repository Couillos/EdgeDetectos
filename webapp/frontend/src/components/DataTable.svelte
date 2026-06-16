<!--
  Generic sortable data table.

  Props:
    columns  — Array<{ key, label, numeric?, sortable?, format? }>
    rows     — Array<object>
    sortCol  — $bindable string
    sortDir  — $bindable 'asc'|'desc'
    rowClass — (row) => string   (e.g. verdict coloring)
    onRowClick — (row) => void
    selectable — boolean (enables checkboxes)
    selected  — $bindable Set<string>
    rowKey   — key field for selection (default 'name')
    emptyMsg — string
-->
<script>
  let {
    columns = [],
    rows = [],
    sortCol = $bindable(''),
    sortDir = $bindable('asc'),
    rowClass = () => '',
    onRowClick = null,
    selectable = false,
    selected = $bindable(new Set()),
    rowKey = 'name',
    emptyMsg = 'No data',
    extraHead = null,
    extraRow = null,
  } = $props()

  function toggleSort(key) {
    if (sortCol === key) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc'
    } else {
      sortCol = key
      sortDir = 'asc'
    }
  }

  function toggleAll(e) {
    if (e.target.checked) {
      selected = new Set(rows.map(r => r[rowKey]))
    } else {
      selected = new Set()
    }
  }

  function toggleRow(key) {
    const s = new Set(selected)
    s.has(key) ? s.delete(key) : s.add(key)
    selected = s
  }

  let allChecked = $derived(rows.length > 0 && rows.every(r => selected.has(r[rowKey])))
</script>

<div class="table-wrap">
  <table class="data-table">
    <thead>
      <tr>
        {#if selectable}
          <th class="w-10 text-center">
            <input type="checkbox" class="checkbox checkbox-xs" checked={allChecked} onchange={toggleAll} />
          </th>
        {/if}
        {#each columns as col}
          <th
            class:sorted={sortCol === col.key}
            class:num={col.numeric}
            class:cursor-pointer={col.sortable !== false}
            onclick={() => col.sortable !== false && toggleSort(col.key)}
          >
            {col.label}{sortCol === col.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
          </th>
        {/each}
        {#if extraHead}
          {@render extraHead()}
        {/if}
      </tr>
    </thead>
    <tbody>
      {#if rows.length === 0}
        <tr>
          <td colspan={columns.length + (selectable ? 1 : 0) + (extraHead ? 1 : 0)}>
            <div class="empty-state"><h3>{emptyMsg}</h3></div>
          </td>
        </tr>
      {:else}
        {#each rows as row (row[rowKey] ?? row)}
          <tr
            class="{rowClass(row)} {selected?.has(row[rowKey]) ? 'selected' : ''}"
            class:cursor-pointer={!!onRowClick}
            onclick={() => onRowClick?.(row)}
          >
            {#if selectable}
              <td class="w-10 text-center" onclick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs"
                  checked={selected.has(row[rowKey])}
                  onchange={() => toggleRow(row[rowKey])}
                />
              </td>
            {/if}
            {#each columns as col}
              <td class:num={col.numeric}>
                {#if col.render}
                  {@render col.render(row)}
                {:else}
                  {col.format ? col.format(row[col.key], row) : (row[col.key] ?? '—')}
                {/if}
              </td>
            {/each}
            {#if extraRow}
              {@render extraRow(row)}
            {/if}
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
