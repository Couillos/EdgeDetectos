import { describe, it, expect } from 'vitest'

// Pure filter helpers — extracted logic matching Ranking.svelte and Oos.svelte
function applyRankFilters(edges, f) {
  return edges.filter(e => {
    if (f.name     && !e.name.toLowerCase().includes(f.name)) return false
    if (f.verdict  && e.verdict !== f.verdict) return false
    if (f.scoreMin  !== '' && (e.score  ?? 0)    < +f.scoreMin)  return false
    if (f.scoreMax  !== '' && (e.score  ?? 0)    > +f.scoreMax)  return false
    if (f.sharpeMin !== '' && (e.sharpe ?? -999) < +f.sharpeMin) return false
    if (f.sharpeMax !== '' && (e.sharpe ?? 999)  > +f.sharpeMax) return false
    if (f.winrateMin!== '' && (e.winrate?? 0)    < +f.winrateMin)return false
    if (f.winrateMax!== '' && (e.winrate?? 100)  > +f.winrateMax)return false
    if (f.tpMin     !== '' && (e.t_p    ?? -1)   < +f.tpMin)    return false
    if (f.tpMax     !== '' && (e.t_p    ?? 2)    > +f.tpMax)    return false
    if (f.mcpMin    !== '' && (e.mc_p   ?? -1)   < +f.mcpMin)   return false
    if (f.mcpMax    !== '' && (e.mc_p   ?? 2)    > +f.mcpMax)   return false
    if (f.kspMin    !== '' && (e.ks_p   ?? -1)   < +f.kspMin)   return false
    if (f.kspMax    !== '' && (e.ks_p   ?? 2)    > +f.kspMax)   return false
    return true
  })
}

function applyOOSFilters(edges, f) {
  return edges.filter(e => {
    if (f.name     && !e.name.toLowerCase().includes(f.name)) return false
    if (f.verdict  && e.verdict !== f.verdict) return false
    if (f.isScMin  !== '' && (e.is_score   ?? 0)   < +f.isScMin)  return false
    if (f.isScMax  !== '' && (e.is_score   ?? 100) > +f.isScMax)  return false
    if (f.oosScMin !== '' && (e.oos_score  ?? 0)   < +f.oosScMin) return false
    if (f.oosScMax !== '' && (e.oos_score  ?? 100) > +f.oosScMax) return false
    if (f.decMin   !== '' && (e.decay      ?? -1)  < +f.decMin)   return false
    if (f.decMax   !== '' && (e.decay      ?? 2)   > +f.decMax)   return false
    if (f.oosMcpMin!== '' && (e.oos_mc_p   ?? -1)  < +f.oosMcpMin)return false
    if (f.oosMcpMax!== '' && (e.oos_mc_p   ?? 2)   > +f.oosMcpMax)return false
    if (f.distKspMin!=='' && (e.dist_ks_p  ?? -1)  < +f.distKspMin)return false
    if (f.distKspMax!=='' && (e.dist_ks_p  ?? 2)   > +f.distKspMax)return false
    return true
  })
}

function sortEdges(edges, col, dir) {
  return [...edges].sort((a, b) => {
    if (!col) return 0
    const av = a[col], bv = b[col]
    if (typeof av === 'string') return dir === 'asc' ? (av||'').localeCompare(bv||'') : (bv||'').localeCompare(av||'')
    return dir === 'asc' ? (av||0)-(bv||0) : (bv||0)-(av||0)
  })
}

const EDGES = [
  { name: 'RSI 14 Oversold', score: 44, verdict: 'STRONG', sharpe: 1.2, winrate: 62.5, total_return: 500, t_p: 0.001, mc_p: 0.02, ks_p: 0.01, sig: 3, breadth: 5 },
  { name: 'MACD Bull Cross', score: 30, verdict: 'PASS',   sharpe: 0.8, winrate: 55.0, total_return: 200, t_p: 0.01,  mc_p: 0.05, ks_p: 0.03, sig: 2, breadth: 3 },
  { name: 'EMA Crossover',   score: 15, verdict: 'WEAK',   sharpe: 0.3, winrate: 48.0, total_return: -50, t_p: 0.5,   mc_p: 0.4,  ks_p: 0.3,  sig: 0, breadth: 1 },
  { name: 'BB Reversal',     score: 5,  verdict: 'FAIL',   sharpe: -0.2,winrate: 35.0, total_return: -200,t_p: 0.9,   mc_p: 0.8,  ks_p: 0.7,  sig: 0, breadth: 0 },
]

const EMPTY_F = { name:'', verdict:'', scoreMin:'', scoreMax:'', sharpeMin:'', sharpeMax:'', winrateMin:'', winrateMax:'', trMin:'', trMax:'', sigMin:'', sigMax:'', breadthMin:'', breadthMax:'', tpMin:'', tpMax:'', mcpMin:'', mcpMax:'', kspMin:'', kspMax:'' }

describe('applyRankFilters()', () => {
  it('returns all on empty filters', () => {
    expect(applyRankFilters(EDGES, EMPTY_F)).toHaveLength(4)
  })
  it('filters by name (case-insensitive)', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, name: 'rsi' })
    expect(r).toHaveLength(1)
    expect(r[0].name).toBe('RSI 14 Oversold')
  })
  it('filters by verdict', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, verdict: 'STRONG' })
    expect(r).toHaveLength(1)
  })
  it('filters by score range', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, scoreMin: '20', scoreMax: '40' })
    expect(r).toHaveLength(1)
    expect(r[0].name).toBe('MACD Bull Cross')
  })
  it('filters by t_p range', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, tpMin: '0', tpMax: '0.05' })
    expect(r).toHaveLength(2)
    r.forEach(e => expect(e.t_p).toBeLessThanOrEqual(0.05))
  })
  it('filters by mc_p range', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, mcpMin: '0', mcpMax: '0.03' })
    expect(r).toHaveLength(1)
    expect(r[0].mc_p).toBeLessThanOrEqual(0.03)
  })
  it('combined filters', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, scoreMin: '10', scoreMax: '50', sharpeMin: '0.5' })
    expect(r).toHaveLength(2)
  })
  it('no match returns empty', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, sharpeMin: '10', sharpeMax: '20' })
    expect(r).toHaveLength(0)
  })
  it('exact winrate match', () => {
    const r = applyRankFilters(EDGES, { ...EMPTY_F, winrateMin: '55', winrateMax: '55' })
    expect(r).toHaveLength(1)
    expect(r[0].name).toBe('MACD Bull Cross')
  })
})

const OOS_EDGES = [
  { name: 'Edge A', verdict: 'STRONG', is_score: 70, oos_score: 65, decay: 0.1, oos_mc_p: 0.01, dist_ks_p: 0.05, is_sharpe: 1.8 },
  { name: 'Edge B', verdict: 'PASS',   is_score: 55, oos_score: 50, decay: 0.3, oos_mc_p: 0.03, dist_ks_p: 0.15, is_sharpe: 1.0 },
  { name: 'Edge C', verdict: 'WEAK',   is_score: 35, oos_score: 30, decay: 0.6, oos_mc_p: 0.4,  dist_ks_p: 0.5,  is_sharpe: 0.3 },
  { name: 'Edge D', verdict: 'FAIL',   is_score: 15, oos_score: 10, decay: 0.9, oos_mc_p: 0.8,  dist_ks_p: 0.9,  is_sharpe: -0.2 },
]
const EMPTY_OOS = { name:'', verdict:'', isScMin:'', isScMax:'', oosScMin:'', oosScMax:'', finalScMin:'', finalScMax:'', decMin:'', decMax:'', isShMin:'', isShMax:'', oosShMin:'', oosShMax:'', oosWrMin:'', oosWrMax:'', oosTpMin:'', oosTpMax:'', oosMcpMin:'', oosMcpMax:'', distKspMin:'', distKspMax:'' }

describe('applyOOSFilters()', () => {
  it('returns all on empty filters', () => {
    expect(applyOOSFilters(OOS_EDGES, EMPTY_OOS)).toHaveLength(4)
  })
  it('filters by name', () => {
    const r = applyOOSFilters(OOS_EDGES, { ...EMPTY_OOS, name: 'edge a' })
    expect(r).toHaveLength(1)
    expect(r[0].name).toBe('Edge A')
  })
  it('filters by verdict', () => {
    expect(applyOOSFilters(OOS_EDGES, { ...EMPTY_OOS, verdict: 'PASS' })).toHaveLength(1)
  })
  it('filters by decay range', () => {
    const r = applyOOSFilters(OOS_EDGES, { ...EMPTY_OOS, decMin: '0.5', decMax: '1' })
    expect(r).toHaveLength(2)
    r.forEach(e => { expect(e.decay).toBeGreaterThanOrEqual(0.5); expect(e.decay).toBeLessThanOrEqual(1) })
  })
  it('filters by oos_mc_p', () => {
    const r = applyOOSFilters(OOS_EDGES, { ...EMPTY_OOS, oosMcpMin: '0', oosMcpMax: '0.05' })
    expect(r).toHaveLength(2)
  })
  it('filters by dist_ks_p', () => {
    const r = applyOOSFilters(OOS_EDGES, { ...EMPTY_OOS, distKspMin: '0', distKspMax: '0.1' })
    expect(r).toHaveLength(1)
  })
})

describe('sortEdges()', () => {
  it('sorts by score desc', () => {
    const s = sortEdges(EDGES, 'score', 'desc')
    expect(s[0].score).toBeGreaterThanOrEqual(s[1].score)
  })
  it('sorts by name asc', () => {
    const s = sortEdges(EDGES, 'name', 'asc')
    expect(s[0].name <= s[1].name).toBe(true)
  })
  it('sorts by t_p asc', () => {
    const s = sortEdges(EDGES, 't_p', 'asc')
    expect(s[0].t_p).toBeLessThanOrEqual(s[1].t_p)
  })
  it('empty col returns original order', () => {
    const s = sortEdges(EDGES, '', 'asc')
    expect(s).toHaveLength(EDGES.length)
  })
  it('handles null values without crash', () => {
    const list = [{ score: 10 }, { score: null }, { score: 5 }]
    expect(() => sortEdges(list, 'score', 'desc')).not.toThrow()
  })
})
