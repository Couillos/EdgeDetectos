<script>
  import { location } from 'svelte-spa-router'

  const nav = [
    {
      route: '/', label: 'Dashboard',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>`,
    },
    {
      route: '/edges', label: 'Edges',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>`,
    },
    {
      route: '/ranking', label: 'Ranking',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 20V10M12 20V4M18 20v-6"/></svg>`,
    },
    {
      route: '/oos', label: 'OOS',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>`,
    },
    {
      route: '/create', label: 'Create Edge',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
    },
  ]

  function isActive(route) {
    if (route === '/') return $location === '/'
    return $location.startsWith(route)
  }
</script>

<div class="sidebar-logo">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>
  Edge Generator
</div>

<nav class="sidebar-nav">
  {#each nav as item}
    <a href="#{item.route}" class:active={isActive(item.route)}>
      {@html item.icon}
      {item.label}
    </a>
  {/each}
</nav>
