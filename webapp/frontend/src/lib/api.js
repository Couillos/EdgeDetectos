export const api = {
  async get(path) {
    const r = await fetch(path)
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
    return r.json()
  },

  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.detail || `${r.status} ${r.statusText}`)
    return data
  },
}
