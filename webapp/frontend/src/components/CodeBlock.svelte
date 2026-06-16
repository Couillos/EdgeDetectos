<script>
  import { onMount } from 'svelte'
  import hljs from 'highlight.js/lib/core'
  import python from 'highlight.js/lib/languages/python'

  hljs.registerLanguage('python', python)

  let { code = '' } = $props()
  let highlighted = $derived(code ? hljs.highlight(code, { language: 'python' }).value : '')
</script>

<pre class="code-block"><code class="language-python">{@html highlighted}</code></pre>
