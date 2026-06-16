<script>
  let { verdict = '', type = 'verdict' } = $props()

  // Map verdict/signal to DaisyUI badge variant
  const verdictClass = {
    STRONG:   'badge-success',
    PASS:     'badge-info',
    WEAK:     'badge-warning',
    FAIL:     'badge-error',
    MODERATE: 'badge-warning',
    NONE:     'badge-ghost',
    long:     'badge-success',
    short:    'badge-error',
    both:     'badge-info',
  }

  let cls = $derived(verdictClass[verdict] || 'badge-ghost')
</script>

{#if verdict}
  <span class="badge badge-sm {cls}">{verdict.toUpperCase()}</span>
{/if}
