<script>
  import { currentTask } from '../lib/stores.js'

  let task     = $derived($currentTask)
  let processed = $derived(task ? (task.processed || (task.completed + task.skipped + task.failed)) : 0)
  let total     = $derived(task?.total || 1)
  let fillPct   = $derived(task ? Math.min(100, (processed / total) * 100) : 0)
</script>

<div class="progress-bar-fixed" class:visible={!!task}>
  <div class="progress-info">
    <span class="progress-label">{task?.label ?? ''}</span>
    <span class="progress-stats">
      {task?.completed ?? 0}/{task?.total ?? 0} done
      ({processed} total · {task?.skipped ?? 0} skipped · {task?.failed ?? 0} failed)
    </span>
  </div>
  <div class="progress-track">
    <div class="progress-fill" style="width:{fillPct}%"></div>
  </div>
</div>
