export const VERDICTS = ['', 'STRONG', 'MODERATE', 'WEAK', 'NONE']

export function verdictBadge(v) {
  switch (v) {
    case 'STRONG':   return 'badge-success'
    case 'MODERATE': return 'badge-info'
    case 'WEAK':     return 'badge-warning'
    case 'NONE':     return 'badge-ghost'
    case 'PASS':     return 'badge-info'
    case 'FAIL':     return 'badge-error'
    default:         return 'badge-ghost'
  }
}

export function num(n, d = 2) {
  if (n == null) return '-'
  const v = Number(n)
  if (isNaN(v) || !isFinite(v)) return '-'
  return v.toFixed(d)
}

export function pct(n) {
  if (n == null) return '-'
  const v = Number(n)
  if (isNaN(v) || !isFinite(v)) return '-'
  return v.toFixed(1) + '%'
}
