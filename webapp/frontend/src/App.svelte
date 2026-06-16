<script>
  import Router from 'svelte-spa-router'
  import { routes } from './routes.js'
  import Sidebar from './components/Sidebar.svelte'
  import ProgressBar from './components/ProgressBar.svelte'
  import Toaster from './components/Toaster.svelte'
  import { onMount } from 'svelte'
  import { tryResumeTask } from './lib/sse.js'

  onMount(tryResumeTask)
</script>

<div class="sidebar">
  <Sidebar />
</div>

<div class="main">
  <div class="main-content page-enter">
    <Router {routes} />
  </div>
</div>

<ProgressBar />
<Toaster />
