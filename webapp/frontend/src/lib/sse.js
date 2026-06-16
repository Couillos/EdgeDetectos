import { currentTask, addToast } from './stores.js'
import { get } from 'svelte/store'

let _hideTimer = null

export function showProgress(label, total) {
  if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null }
  currentTask.set({ label, total, completed: 0, skipped: 0, failed: 0, processed: 0, start: Date.now() })
}

export function hideProgress() {
  if (_hideTimer) clearTimeout(_hideTimer)
  _hideTimer = setTimeout(() => {
    _hideTimer = null
    currentTask.set(null)
  }, 2000)
}

export function connectSSE(url, onProgress, onComplete) {
  let retries = 0

  function connect() {
    const es = new EventSource(url)

    es.addEventListener('progress', e => {
      retries = 0
      const d = JSON.parse(e.data)
      currentTask.update(t => {
        if (!t) return t
        return {
          ...t,
          completed: d.completed || 0,
          total: d.total || 0,
          processed: d.processed || 0,
          skipped: d.status === 'skip' ? (t.skipped || 0) + 1 : (t.skipped || 0),
          failed:   d.status === 'fail' ? (t.failed  || 0) + 1 : (t.failed  || 0),
        }
      })
      onProgress?.(d)
    })

    es.addEventListener('complete', e => {
      const d = JSON.parse(e.data)
      es.close()
      try { sessionStorage.removeItem('active_task') } catch {}
      onComplete?.(d)
      addToast(`Done: ${d.completed} done, ${d.skipped} skipped, ${d.failed} failed in ${d.elapsed?.toFixed(1)}s`, 'success')
      hideProgress()
    })

    es.onerror = () => {
      es.close()
      const task = get(currentTask)
      if (retries < 10 && task) {
        retries++
        setTimeout(connect, 2000 * Math.min(retries, 5))
      } else {
        try { sessionStorage.removeItem('active_task') } catch {}
        hideProgress()
        addToast('Connection lost', 'error')
      }
    }

    return es
  }

  return connect()
}

/** Try to reconnect to an in-progress task saved in sessionStorage. */
export function tryResumeTask() {
  try {
    const raw = sessionStorage.getItem('active_task')
    if (!raw) return
    const active = JSON.parse(raw)
    if (!active?.url) return

    currentTask.set({
      label: active.label || 'Reconnecting…',
      total: active.total || 0,
      completed: active.completed || 0,
      skipped: 0, failed: 0, processed: 0,
      start: Date.now(),
    })

    const cleanup = setTimeout(() => {
      try { sessionStorage.removeItem('active_task') } catch {}
      hideProgress()
    }, 6000)

    connectSSE(active.url, null, () => {
      clearTimeout(cleanup)
      try { sessionStorage.removeItem('active_task') } catch {}
      hideProgress()
    })
  } catch {}
}
