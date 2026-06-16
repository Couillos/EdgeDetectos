import { writable } from 'svelte/store'

const LS_KEY = 'edge_state_v2'

function loadAll() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) ?? {} } catch { return {} }
}

function saveAll(data) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(data)) } catch {}
}

function persisted(key, initial) {
  const saved = loadAll()
  const store = writable(saved[key] ?? initial)
  store.subscribe(v => {
    const all = loadAll()
    all[key] = v
    saveAll(all)
  })
  return store
}

// Edge list state
export const edgeSearch  = persisted('search', '')
export const edgeStatus  = persisted('status', 'all')
export const edgeSymbol  = persisted('symbol', '')
export const edgeSortBy  = persisted('sortBy', 'name')
export const edgeSortDir = persisted('sortOrder', 'asc')
export const edgePage    = persisted('page', 1)
export const selectedEdges = writable(new Set())

// Dashboard
export const dashboardSymbols = persisted('dashboardSymbols', [])

// Detail
export const detailSymbol = persisted('detailSymbol', 'BTC/USDT')

// Ranking
export const rankingSymbol  = persisted('rankingSymbol', 'BTC/USDT')
export const rankFilters    = persisted('rankFilters', {
  name:'', verdict:'', scoreMin:'', scoreMax:'',
  sharpeMin:'', sharpeMax:'', winrateMin:'', winrateMax:'',
  trMin:'', trMax:'', sigMin:'', sigMax:'',
  breadthMin:'', breadthMax:'', tpMin:'', tpMax:'',
  mcpMin:'', mcpMax:'', kspMin:'', kspMax:'',
})
export const rankSort = persisted('rankSort', { col: 'score', dir: 'desc' })

// OOS
export const oosSymbol  = persisted('oosSymbol', 'BTC/USDT')
export const oosFilters = persisted('oosFilters', {
  name:'', verdict:'',
  isScMin:'', isScMax:'', oosScMin:'', oosScMax:'',
  finalScMin:'', finalScMax:'', decMin:'', decMax:'',
  isShMin:'', isShMax:'', oosShMin:'', oosShMax:'',
  oosWrMin:'', oosWrMax:'', oosTpMin:'', oosTpMax:'',
  oosMcpMin:'', oosMcpMax:'', distKspMin:'', distKspMax:'',
})
export const oosSort = persisted('oosSort', { col: 'final_score', dir: 'desc' })

// Global task (progress bar)
export const currentTask = writable(null)

// Toasts
export const toasts = writable([])

let _toastId = 0
export function addToast(msg, type = 'info') {
  const id = ++_toastId
  toasts.update(list => [...list, { id, msg, type }])
  setTimeout(() => toasts.update(list => list.filter(t => t.id !== id)), 3500)
}
