import { api } from './api.js'
import { get } from 'svelte/store'
import { dashboardSymbols, detailSymbol, edgeSymbol, currentTask, addToast } from './stores.js'
import { showProgress, connectSSE, hideProgress } from './sse.js'

export function startAnalysis(edgeNames, force = false, quick = false, symbols = null, workers = null, onDone = null) {
  const names = Array.isArray(edgeNames) ? edgeNames : null
  if (!symbols) {
    const ds = get(dashboardSymbols)
    symbols = ds.length > 0 ? ds : [get(edgeSymbol) || 'BTC/USDT']
  }
  const symbolsStr = symbols.join(',')
  const label = names ? `Analyzing ${names.length} edge(s)` : `Analyzing all edges (${symbols.length} symbol(s))`
  showProgress(label, names ? names.length : 0)

  api.post('/api/analyze', {
    symbol: symbols[0],
    symbols: symbolsStr,
    edge_name: names?.length === 1 ? names[0] : null,
    quick,
    force,
    workers,
    since: '2020-01-01',
    until: new Date().toISOString().slice(0, 10),
  }).then(resp => {
    const task = get(currentTask)
    try {
      sessionStorage.setItem('active_task', JSON.stringify({
        url: `/api/analyze/${resp.task_id}/progress`,
        type: 'analyze',
        label: task?.label,
        total: task?.total,
        completed: task?.completed,
      }))
    } catch {}
    connectSSE(`/api/analyze/${resp.task_id}/progress`, null, () => {
      try { sessionStorage.removeItem('active_task') } catch {}
      onDone?.()
    })
  }).catch(e => {
    hideProgress()
    addToast(`Error: ${e.message}`, 'error')
  })
}

export function startOOS(symbol, workers = null, onDone = null) {
  showProgress('Running OOS Validation', 0)
  api.post('/api/oos-validate', {
    symbol,
    since: '2020-01-01',
    until: new Date().toISOString().slice(0, 10),
    workers,
  }).then(resp => {
    const task = get(currentTask)
    try {
      sessionStorage.setItem('active_task', JSON.stringify({
        url: `/api/oos-validate/${resp.task_id}/progress`,
        type: 'oos',
        label: task?.label,
        total: task?.total,
        completed: task?.completed,
      }))
    } catch {}
    connectSSE(`/api/oos-validate/${resp.task_id}/progress`, null, () => {
      try { sessionStorage.removeItem('active_task') } catch {}
      onDone?.()
    })
  }).catch(e => {
    hideProgress()
    addToast(`Error: ${e.message}`, 'error')
  })
}
