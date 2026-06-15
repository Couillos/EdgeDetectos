const LS_KEY = 'edge_state';
function _saveState() {
  const saveable = {
    search: state.search, status: state.status, symbol: state.symbol, sortBy: state.sortBy, sortOrder: state.sortOrder, page: state.page,
    rankFilters: state.rankFilters, rankSort: state.rankSort,
    oosFilters: state.oosFilters, oosSort: state.oosSort, oosSymbol: state.oosSymbol,
    dashboardSymbols: state.dashboardSymbols,
    detailSymbol: state.detailSymbol,
  };
  try { localStorage.setItem(LS_KEY, JSON.stringify(saveable)); } catch (_) {}
}
function _loadState() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    Object.assign(state, saved);
  } catch (_) {}
}

const state = { edges: [], symbols: [], currentTask: null, selectedEdges: new Set(), sortBy: 'name', sortOrder: 'asc', page: 1, perPage: 50, search: '', status: 'all', symbol: '', dashboardSymbols: [], detailSymbol: 'BTC/USDT', rankFilters: { name: '', verdict: '', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' }, rankSort: { col: 'score', dir: 'desc' }, oosFilters: { name: '', verdict: '', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '', oosMcpMax: '', distKspMin: '', distKspMax: '' }, oosSort: { col: 'final_score', dir: 'desc' }, oosSymbol: 'BTC/USDT' };
_loadState();
const events = { _listeners: {}, on(e, fn) { (this._listeners[e] = this._listeners[e] || []).push(fn); }, emit(e, data) { (this._listeners[e] || []).forEach(fn => fn(data)); } };
const api = {
  async get(path) { const r = await fetch(path); if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); },
  async post(path, body) {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json(); if (!r.ok) throw new Error(data.detail || `${r.status} ${r.statusText}`);
    return data;
  }
};

function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return document.querySelectorAll(sel); }
function $el(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'className') el.className = v;
    else if (k === 'onclick') el.onclick = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    if (typeof c === 'string' && c.trim().startsWith('<')) el.insertAdjacentHTML('beforeend', c);
    else if (typeof c === 'string') el.append(document.createTextNode(c));
    else el.append(c);
  }
  return el;
}
function num(n, d = 2) { if (n == null) return '-'; const v = Number(n); if (isNaN(v) || !isFinite(v)) return '-'; return v.toFixed(d); }
function pct(n) { if (n == null) return '-'; const v = Number(n); if (isNaN(v) || !isFinite(v)) return '-'; return v.toFixed(1) + '%'; }

/* Toast */
function toast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  const t = $el('div', { className: `toast ${type}` }, msg);
  c.appendChild(t);
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 500); }, 3000);
}

/* Progress bar */
function showProgress(label, total) {
  state.currentTask = { label, total, completed: 0, skipped: 0, failed: 0, start: Date.now() };
  const bar = document.getElementById('progress-bar');
  bar.classList.add('visible');
  updateProgress();
}
function updateProgress() {
  const t = state.currentTask; if (!t) return;
  const done = t.completed || 0, skipped = t.skipped || 0, failed = t.failed || 0;
  const processed = t.processed || (done + skipped + failed);
  const total = t.total || 1;
  const pct = Math.min(100, (processed / total) * 100);
  const elapsed = ((Date.now() - t.start) / 1000).toFixed(1);
  qs('#progress-label').textContent = t.label;
  qs('#progress-stats').textContent = `${done}/${total} done (${processed} total, ${skipped} skipped, ${failed} failed)`;
  qs('#progress-fill').style.width = pct + '%';
  qs('#progress-elapsed').textContent = `${elapsed}s`;
}
function hideProgress() {
  const bar = document.getElementById('progress-bar');
  setTimeout(() => { bar.classList.remove('visible'); state.currentTask = null; }, 2000);
}

/* SSE */
function connectSSE(url, onProgress, onComplete) {
  let retries = 0;
  function connect() {
    const es = new EventSource(url);
    es.addEventListener('progress', e => {
      retries = 0;
      const d = JSON.parse(e.data);
      if (state.currentTask) {
        state.currentTask.completed = d.completed || 0;
        state.currentTask.total = d.total || 0;
        state.currentTask.processed = d.processed || 0;
        if (d.status === 'skip') state.currentTask.skipped++;
        if (d.status === 'fail') state.currentTask.failed++;
        updateProgress();
      }
      if (onProgress) onProgress(d);
    });
    es.addEventListener('complete', e => {
      const d = JSON.parse(e.data);
      es.close();
      try { sessionStorage.removeItem('active_task'); } catch (_) {}
      if (onComplete) onComplete(d);
      toast(`Done: ${d.completed} done, ${d.skipped} skipped, ${d.failed} failed in ${d.elapsed.toFixed(1)}s`, 'success');
      hideProgress();
    });
    es.onerror = () => {
      es.close();
      if (retries < 10 && state.currentTask) {
        retries++;
        setTimeout(connect, 2000 * Math.min(retries, 5));
      } else {
        try { sessionStorage.removeItem('active_task'); } catch (_) {}
        hideProgress();
        toast('Connection lost', 'error');
      }
    };
    return es;
  }
  return connect();
}

/* Router */
function navigate(hash) { window.location.hash = hash; }
function getRoute() {
  const h = window.location.hash.slice(1) || '/';
  const m = h.match(/^\/edges\/(.+)/); if (m) return { page: 'edge-detail', name: decodeURIComponent(m[1]) };
  if (h === '/edges') return { page: 'edges' };
  if (h === '/ranking') return { page: 'ranking' };
  if (h === '/oos') return { page: 'oos' };
  if (h === '/create') return { page: 'create' };
  return { page: 'dashboard' };
}

/* Router */
function initRouter() {
  const render = () => {
    const route = getRoute();
    const main = qs('.main-content');
    if (!main) return;
    main.innerHTML = '';
    main.classList.remove('page-enter');
    renderPage(route, main);
    setTimeout(() => main.classList.add('page-enter'), 10);
    qsa('.sidebar-nav a').forEach(a => a.classList.toggle('active', a.dataset.route === route.page || (route.page === 'edge-detail' && a.dataset.route === 'edges')));
  };
  window.addEventListener('hashchange', render);
  render();
}

/* Sidebar */
function renderSidebar() {
  const routes = [
    { route: 'dashboard', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>', label: 'Dashboard' },
    { route: 'edges', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>', label: 'Edges' },
    { route: 'ranking', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 20V10M12 20V4M18 20v-6"/></svg>', label: 'Ranking' },
    { route: 'oos', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>', label: 'OOS' },
    { route: 'create', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', label: 'Create Edge' },
  ];
  return $el('nav', { className: 'sidebar-nav' }, ...routes.map(r =>
    $el('a', { href: '#' + (r.route === 'dashboard' ? '/' : '/' + r.route), dataset: { route: r.route } }, r.icon, ' ', r.label)
  ));
}

/* Render App Layout */
function renderApp() {
  const app = qs('#app');
  app.innerHTML = '';
  const sidebar = $el('div', { className: 'sidebar' },
    $el('div', { className: 'sidebar-logo' },
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Edge Generator'
    ),
    renderSidebar()
  );
  const main = $el('div', { className: 'main' },
    $el('div', { id: 'main-header', className: 'main-header' }),
    $el('div', { className: 'main-content', id: 'main-content' })
  );
  app.append(sidebar, main);
  initRouter();
}

/* Page Router */
function renderPage(route, container) {
  const header = qs('#main-header');
  switch (route.page) {
    case 'dashboard': header.innerHTML = '<h1>Dashboard</h1>'; renderDashboard(container); break;
    case 'edges': header.innerHTML = '<h1>Edges</h1>'; renderEdgeList(container); break;
    case 'edge-detail': header.innerHTML = ''; renderEdgeDetail(container, route.name); break;
    case 'ranking': header.innerHTML = '<h1>Ranking</h1>'; renderRanking(container); break;
    case 'oos': header.innerHTML = '<h1>OOS Validation</h1>'; renderOOS(container); break;
    case 'create': header.innerHTML = '<h1>Create Edge</h1>'; renderCreateEdge(container); break;
    default: header.innerHTML = '<h1>404</h1>'; container.innerHTML = '<div class="empty-state"><h3>Page not found</h3></div>';
  }
}

/* ============ DASHBOARD ============ */
async function renderDashboard(container) {
  container.innerHTML = '<div class="flex justify-center" style="padding:60px"><div class="spinner"></div></div>';
  try {
    const symbols = await api.get('/api/symbols');
    // Restore selection: if empty and symbols exist, default to all
    if (state.dashboardSymbols.length === 0 && symbols.length > 0) {
      state.dashboardSymbols = [...symbols];
    }

    const selSymbols = state.dashboardSymbols.length > 0 ? state.dashboardSymbols : symbols;

    // Fetch edge stats for each selected symbol in parallel
    const results = await Promise.all(selSymbols.map(sym =>
      Promise.all([
        api.get(`/api/edges?per_page=1&status=all&symbol=${encodeURIComponent(sym)}`),
        api.get(`/api/edges?per_page=1&status=analyzed&symbol=${encodeURIComponent(sym)}`),
      ])
    ));
    let total = 0, analyzed = 0, pending = 0;
    for (const [allData, analyzedData] of results) {
      const t = allData.total || 0;
      const a = analyzedData.total || 0;
      total += t;
      analyzed += a;
      pending += t - a;
    }

    container.innerHTML = '';

    // Symbol multi-select
    const selContainer = $el('div', { className: 'dashboard-symbol-select', style: { marginBottom: '16px' } },
      $el('label', { style: { fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' } }, 'Symbols to analyze:'),
    );
    const select = $el('select', { multiple: true, style: { width: '100%', minHeight: '80px' } });
    const allSelected = selSymbols.length === symbols.length;
    const allOpt = $el('option', { value: '__all__' }, 'All Symbols');
    if (allSelected) allOpt.selected = true;
    select.append(allOpt);
    for (const sym of symbols) {
      const opt = $el('option', { value: sym }, sym);
      if (selSymbols.includes(sym)) opt.selected = true;
      select.append(opt);
    }
    select.onchange = () => {
      const selected = Array.from(select.selectedOptions).map(o => o.value);
      if (selected.includes('__all__') || selected.length === 0 || selected.length === symbols.length) {
        state.dashboardSymbols = [...symbols];
      } else {
        state.dashboardSymbols = selected.filter(s => s !== '__all__');
      }
      _saveState();
      renderDashboard(container);
    };
    selContainer.append(select);
    container.append(selContainer);

    const cards = $el('div', { className: 'cards-grid' },
      $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, String(total)), $el('div', { className: 'card-label' }, 'Total Edges')),
      $el('div', { className: 'card' }, $el('div', { className: 'card-value text-green' }, String(analyzed)), $el('div', { className: 'card-label' }, 'Analyzed')),
      $el('div', { className: 'card' }, $el('div', { className: 'card-value text-yellow' }, String(pending)), $el('div', { className: 'card-label' }, 'Pending')),
      $el('div', { className: 'card' }, $el('div', { className: 'card-value text-blue' }, String(symbols.length)), $el('div', { className: 'card-label' }, 'Symbols')),
    );
    container.append(cards);

    const actions = $el('div', { className: 'flex gap-8', style: { marginBottom: '24px' } },
      $el('button', { className: 'btn btn-primary', onclick: () => startAnalysis(null, true, false, selSymbols) },
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px"><polygon points="5 3 19 12 5 21 5 3"/></svg> Analyze All'
      ),
      $el('button', { className: 'btn', onclick: () => navigate('/ranking') }, 'View Ranking'),
      $el('button', { className: 'btn', onclick: () => navigate('/oos') }, 'OOS Validation'),
    );
    container.append(actions);

    if (analyzed > 0 && results.length > 0) {
      const firstResult = results[0][1];
      const last = firstResult.edges && firstResult.edges[0];
      if (last) {
        const info = $el('div', { className: 'card' },
          $el('div', { style: { fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' } }, 'Last Analysis'),
          $el('div', { style: { fontSize: '14px' } }, `Latest edge: ${last.name}`),
          $el('div', { className: 'flex gap-8', style: { marginTop: '8px' } },
            last.verdict && $el('span', { className: `badge badge-${last.verdict}` }, last.verdict),
            last.best_sharpe != null && $el('span', { style: { fontSize: '12px', color: 'var(--text-secondary)' } }, `Sharpe: ${num(last.best_sharpe)}`),
          )
        );
        container.append(info);
      }
    }
  } catch (e) { container.innerHTML = `<div class="empty-state"><h3>Error loading dashboard</h3><p>${e.message}</p></div>`; }
}

/* ============ EDGE LIST ============ */
async function renderEdgeList(container) {
  container.innerHTML = '';
  const toolbar = $el('div', { className: 'toolbar' });
  const searchInput = $el('input', { className: 'input search-input', placeholder: 'Search edges...', type: 'text' });
  const symbolSelect = $el('select', { className: 'form-select', style: { width: 'auto', minWidth: '140px' } },
    $el('option', { value: '' }, 'All Symbols')
  );
  const statusSelect = $el('select', { className: 'form-select', style: { width: 'auto', minWidth: '120px' } },
    $el('option', { value: 'all' }, 'All'),
    $el('option', { value: 'analyzed' }, 'Analyzed'),
    $el('option', { value: 'pending' }, 'Pending'),
  );
  toolbar.append(searchInput, symbolSelect, statusSelect);
  container.append(toolbar);

  const tableWrap = $el('div', { className: 'table-wrap' });
  const table = $el('table', { className: 'data-table', id: 'edge-table' });
  tableWrap.append(table);
  container.append(tableWrap);
  const paginationDiv = $el('div', { className: 'pagination', id: 'edge-pagination' });
  container.append(paginationDiv);

  const actionBar = $el('div', { id: 'edge-action-bar', style: { display: 'none', marginBottom: '12px' } },
    $el('button', { className: 'btn btn-primary btn-sm', onclick: () => {
      const names = Array.from(state.selectedEdges);
      if (names.length) startAnalysis(names);
    } }, `Analyze Selected (${state.selectedEdges.size})`)
  );
  container.prepend(actionBar);

  let debounceTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { state.search = searchInput.value; state.page = 1; loadEdges(); }, 300);
  });
  symbolSelect.addEventListener('change', () => { state.symbol = symbolSelect.value; state.page = 1; loadEdges(); });
  statusSelect.addEventListener('change', () => { state.status = statusSelect.value; state.page = 1; loadEdges(); });

  let allEdges = [];

  async function loadEdges() {
    const params = new URLSearchParams({ search: state.search, status: state.status });
    if (state.symbol) params.set('symbol', state.symbol);
    params.set('per_page', '200');
    table.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:40px"><div class="spinner"></div></td></tr>';
    try {
      const data = await api.get('/api/edges?' + params.toString());
      allEdges = data.edges || [];
      sortAndRender();
      _saveState();
    } catch (e) { table.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:40px;color:var(--accent-red)">Error: ${e.message}</td></tr>`; }
  }

  function sortAndRender() {
    const col = state.sortBy, dir = state.sortOrder;
    const sorted = [...allEdges].sort((a, b) => {
      let av = a[col], bv = b[col];
      if (col === 'name' || col === 'signal_type' || col === 'verdict') {
        av = (av || '').toLowerCase(); bv = (bv || '').toLowerCase();
        return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      av = av ?? (dir === 'asc' ? 999999 : -999999);
      bv = bv ?? (dir === 'asc' ? 999999 : -999999);
      return dir === 'asc' ? av - bv : bv - av;
    });
    const start = (state.page - 1) * state.perPage;
    const paged = sorted.slice(start, start + state.perPage);
    renderEdgeTable({ edges: paged, total: sorted.length });
  }

  function renderEdgeTable(data) {
    const edges = data.edges || [];
    const total = data.total || 0;
    const totalPages = Math.ceil(total / state.perPage);
    const sortDir = (col) => state.sortBy === col ? (state.sortOrder === 'asc' ? ' ▲' : ' ▼') : '';

    const makeSortFn = (col) => () => {
      if (state.sortBy === col) state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
      else { state.sortBy = col; state.sortOrder = 'asc'; }
      sortAndRender();
    };

    const thead = $el('thead');
    const hrow = $el('tr', {},
      $el('th', { className: 'checkbox-cell' },
        $el('input', { type: 'checkbox', onchange: (e) => {
          const checked = e.target.checked;
          state.selectedEdges.clear();
          if (checked) edges.forEach(e => state.selectedEdges.add(e.name));
          loadEdges();
        } })
      ),
      $el('th', { onclick: makeSortFn('name') }, 'Name', sortDir('name')),
      $el('th', { onclick: makeSortFn('signal_type') }, 'Type', sortDir('signal_type')),
      $el('th', { onclick: makeSortFn('verdict') }, 'Verdict', sortDir('verdict')),
      $el('th', { onclick: makeSortFn('best_sharpe') }, 'Sharpe', sortDir('best_sharpe')),
      $el('th', { onclick: makeSortFn('best_winrate') }, 'Win Rate', sortDir('best_winrate')),
      $el('th', { onclick: makeSortFn('total_signals') }, 'Signals', sortDir('total_signals')),
      $el('th', 'Actions'),
    );
    thead.appendChild(hrow);
    table.innerHTML = '';
    table.appendChild(thead);

    const tbody = $el('tbody');
    if (!edges.length) {
      tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><h3>No edges found</h3></div></td></tr>';
    } else {
      edges.forEach(e => {
        const sel = state.selectedEdges.has(e.name);
        const tr = $el('tr', { className: sel ? 'selected' : '' },
          $el('td', { className: 'checkbox-cell' },
            $el('input', { type: 'checkbox', checked: sel, onchange: (ev) => {
              if (ev.target.checked) state.selectedEdges.add(e.name);
              else state.selectedEdges.delete(e.name);
              updateActionBar();
            } })
          ),
          $el('td', {}, $el('a', { href: '#', onclick: (ev) => { ev.preventDefault(); navigate(`/edges/${encodeURIComponent(e.name)}`); }, className: 'truncate', style: { maxWidth: '280px', display: 'inline-block' } }, e.name)),
          $el('td', {}, $el('span', { className: `badge badge-${e.signal_type || 'both'}` }, (e.signal_type || 'both').toUpperCase())),
          $el('td', {}, e.verdict ? $el('span', { className: `badge badge-${e.verdict}` }, e.verdict) : $el('span', { style: { color: 'var(--text-secondary)' } }, '—')),
          $el('td', { style: { fontFamily: 'monospace' } }, e.best_sharpe != null ? num(e.best_sharpe) : '—'),
          $el('td', { style: { fontFamily: 'monospace' } }, e.best_winrate != null ? pct(e.best_winrate) : '—'),
          $el('td', { style: { fontFamily: 'monospace' } }, e.total_signals != null ? String(e.total_signals) : '—'),
          $el('td', {},
            $el('button', { className: 'btn btn-sm', onclick: () => navigate(`/edges/${encodeURIComponent(e.name)}`) }, 'View'),
            !e.has_analysis ? $el('button', { className: 'btn btn-sm', style: { marginLeft: '4px' }, onclick: () => startAnalysis([e.name]) }, 'Run') : null
          ),
        );
        tbody.appendChild(tr);
      });
    }
    table.appendChild(tbody);
    updateActionBar();

    paginationDiv.innerHTML = '';
    if (totalPages > 1) {
      const prevBtn = $el('button', { className: 'btn btn-sm', disabled: state.page <= 1, onclick: () => { state.page--; sortAndRender(); } }, 'Prev');
      paginationDiv.append(prevBtn);
      const startP = Math.max(1, state.page - 2);
      const endP = Math.min(totalPages, state.page + 2);
      for (let i = startP; i <= endP; i++) {
        const btn = $el('button', { className: `btn btn-sm${i === state.page ? ' btn-primary' : ''}`, onclick: () => { state.page = i; sortAndRender(); } }, String(i));
        paginationDiv.append(btn);
      }
      const nextBtn = $el('button', { className: 'btn btn-sm', disabled: state.page >= totalPages, onclick: () => { state.page++; sortAndRender(); } }, 'Next');
      paginationDiv.append(nextBtn);
      paginationDiv.append($el('span', { className: 'page-info' }, `${state.page}/${totalPages} (${total} total)`));
    }
  }

  function updateActionBar() {
    const bar = document.getElementById('edge-action-bar');
    if (!bar) return;
    if (state.selectedEdges.size > 0) {
      bar.style.display = 'block';
      bar.querySelector('button').textContent = `Analyze Selected (${state.selectedEdges.size})`;
    } else { bar.style.display = 'none'; }
  }

  // Load symbols
  try {
    const syms = await api.get('/api/symbols');
    syms.forEach(s => symbolSelect.append($el('option', { value: s }, s)));
  } catch (_) {}

  state.page = 1;
  loadEdges();
}

/* ============ EDGE DETAIL ============ */
async function renderEdgeDetail(container, name) {
  container.innerHTML = '<div class="flex justify-center" style="padding:60px"><div class="spinner"></div></div>';
  try {
    const [edge, symbols] = await Promise.all([
      api.get(`/api/edges/${encodeURIComponent(name)}?symbol=${encodeURIComponent(state.detailSymbol)}`),
      api.get('/api/symbols')
    ]);
    container.innerHTML = '';

    // Symbol selector
    const symSelect = $el('select', { className: 'form-select', style: { width: 'auto', minWidth: '160px', marginBottom: '16px' } });
    for (const sym of symbols) {
      const opt = $el('option', { value: sym }, sym);
      if (sym === state.detailSymbol) opt.selected = true;
      symSelect.append(opt);
    }
    symSelect.onchange = () => {
      state.detailSymbol = symSelect.value;
      _saveState();
      renderEdgeDetail(container, name);
    };

    const header = $el('div', { className: 'detail-header' },
      $el('h1', {}, edge.signal_name || name),
      symSelect,
      edge.description ? $el('div', { className: 'subtitle' }, edge.description) : null,
      $el('div', { className: 'detail-meta' },
        edge.verdict ? $el('span', { className: `badge badge-${edge.verdict}` }, edge.verdict) : null,
        edge.best_horizon ? $el('span', { style: { fontSize: '13px', color: 'var(--text-secondary)' } }, `Best: ${edge.best_horizon}`) : null,
        edge.source_file ? $el('span', { style: { fontSize: '12px', color: 'var(--text-secondary)' } }, edge.source_file.split('/').pop()) : null,
        edge.total_signals != null ? $el('span', { style: { fontSize: '13px', color: 'var(--text-secondary)' } }, `${edge.total_signals} signals`) : null,
      ),
      $el('div', { className: 'detail-actions' },
        $el('button', { className: 'btn btn-primary btn-sm', onclick: () => startAnalysis([name], true, false, [state.detailSymbol]) }, 'Re-run Analysis'),
        $el('button', { className: 'btn btn-sm', onclick: () => navigate('/ranking') }, 'View Ranking'),
      ),
    );
    container.append(header);

    // Horizon stats table
    const horizons = edge.horizons;
    if (horizons && Object.keys(horizons).length) {
      const section = $el('div', { className: 'detail-section' },
        $el('h2', {}, 'Horizon Stats'),
        $el('div', { className: 'table-wrap' },
          $el('table', { className: 'data-table horizon-table' },
            $el('thead', {},
              $el('tr', {},
                $el('th', 'Horizon'), $el('th', { className: 'num' }, 'Signals'), $el('th', { className: 'num' }, 'Mean %'), $el('th', { className: 'num' }, 'Win Rate'), $el('th', { className: 'num' }, 'Sharpe'), $el('th', { className: 'num' }, 't-p'), $el('th', { className: 'num' }, 'MC p'), $el('th', { className: 'num' }, 'Return %'),
              )
            ),
            $el('tbody', {}, ...Object.entries(horizons).map(([h, d]) => {
              const isBest = String(edge.best_horizon_num) === h;
              return $el('tr', { className: isBest ? 'best' : '' },
                $el('td', { style: { fontWeight: isBest ? 600 : 400 } }, `+${h}h`),
                $el('td', { className: 'num' }, String(d.n_signals)),
                $el('td', { className: 'num' }, num(d.mean * 100)),
                $el('td', { className: 'num' }, pct(d.winrate)),
                $el('td', { className: 'num' }, num(d.sharpe)),
                $el('td', { className: 'num' }, num(d.t_p, 4)),
                $el('td', { className: 'num' }, num(d.mc_p, 4)),
                $el('td', { className: 'num' }, num(d.total_return, 2)),
              );
            })),
          )
        )
      );
      container.append(section);
    }

    // Analysis report image
    if (horizons && Object.keys(horizons).length > 0) {
      const reportSection = $el('div', { className: 'detail-section' },
        $el('h2', {}, 'Analysis Report'),
      );
      if (edge.report_png) {
        const wrap = $el('div', { className: 'report-image-wrap' });
        const symParam = state.detailSymbol ? `?symbol=${encodeURIComponent(state.detailSymbol)}` : '';
        const img = $el('img', { src: edge.report_png + symParam, alt: `Report for ${edge.signal_name}`, style: { width: '100%', maxWidth: '1200px', display: 'block', margin: '0 auto', border: '1px solid var(--border)', borderRadius: '8px' } });
        img.onerror = () => {
          wrap.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-secondary);font-size:14px">Report image not available (analysis was run with --quick).</div>';
        };
        wrap.appendChild(img);
        reportSection.appendChild(wrap);
      } else {
        reportSection.appendChild($el('div', { style: { padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' } },
          'No report image generated yet.',
          $el('button', { className: 'btn btn-sm', style: { marginLeft: '8px' }, onclick: () => startAnalysis([edge.signal_name], true, false, [state.detailSymbol]) }, 'Generate Report')
        ));
      }
      container.append(reportSection);
    }

    // Persistence
    if (edge.persistence) {
      const p = edge.persistence;
      const pSection = $el('div', { className: 'detail-section' },
        $el('h2', {}, 'Persistence'),
        $el('div', { className: 'cards-grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' } },
          $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, `${p.rolling_windows_positive_pct.toFixed(1)}%`), $el('div', { className: 'card-label' }, 'Windows Positive')),
          $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, `${p.years_positive}/${p.years_total}`), $el('div', { className: 'card-label' }, 'Years Positive')),
        )
      );
      container.append(pSection);
    }

    // Tests
    if (edge.tests) {
      const t = edge.tests;
      const tSection = $el('div', { className: 'detail-section' },
        $el('h2', {}, 'Statistical Tests'),
        $el('div', { className: 'cards-grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' } },
          $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, String(t.tests_significant ?? 0)), $el('div', { className: 'card-label' }, 'Tests Significant')),
          t.best_t_test_p != null ? $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, num(t.best_t_test_p, 4)), $el('div', { className: 'card-label' }, 'Best t-test p')) : null,
          t.best_mc_p != null ? $el('div', { className: 'card' }, $el('div', { className: 'card-value' }, num(t.best_mc_p, 4)), $el('div', { className: 'card-label' }, 'Best MC p')) : null,
        )
      );
      container.append(tSection);
    }

    // Raw JSON toggle
    const jsonToggle = $el('div', { className: 'detail-section' },
      $el('div', { className: 'collapsible', onclick: function() { this.classList.toggle('open'); } },
        $el('span', { className: 'chevron' }, '▶ '),
        $el('span', { style: { fontSize: '14px', fontWeight: 600 } }, 'Raw JSON'),
      ),
      $el('div', { className: 'collapsible-content' },
        $el('pre', { className: 'raw-json' }, JSON.stringify(edge, null, 2))
      )
    );
    container.append(jsonToggle);

  } catch (e) { container.innerHTML = `<div class="empty-state"><h3>Error loading edge</h3><p>${e.message}</p></div>`; }
}

/* ============ RANKING ============ */
async function renderRanking(container) {
  container.innerHTML = '';
  const toolbar = $el('div', { className: 'toolbar' },
    $el('select', { id: 'ranking-symbol', className: 'form-select', style: { width: 'auto', minWidth: '160px' } },
      $el('option', { value: 'BTC/USDT' }, 'BTC/USDT')
    ),
  );
  container.append(toolbar);
  const chartDiv = $el('div', { className: 'chart-container' },
    $el('canvas', { id: 'ranking-chart' })
  );
  container.append(chartDiv);
  const filterBar = $el('div', { className: 'filter-bar', id: 'rank-filter-bar' });
  container.append(filterBar);
  const tableDiv = $el('div', { className: 'table-wrap', id: 'ranking-table-wrap' });
  container.append(tableDiv);

  let edges = [];

  function applyRankFilters() {
    return edges.filter(e => {
      const f = state.rankFilters;
      if (f.name && !e.name.toLowerCase().includes(f.name)) return false;
      if (f.verdict && e.verdict !== f.verdict) return false;
      if (f.scoreMin !== '' && (e.score ?? 0) < Number(f.scoreMin)) return false;
      if (f.scoreMax !== '' && (e.score ?? 0) > Number(f.scoreMax)) return false;
      if (f.sharpeMin !== '' && (e.sharpe ?? -999) < Number(f.sharpeMin)) return false;
      if (f.sharpeMax !== '' && (e.sharpe ?? 999) > Number(f.sharpeMax)) return false;
      if (f.winrateMin !== '' && (e.winrate ?? 0) < Number(f.winrateMin)) return false;
      if (f.winrateMax !== '' && (e.winrate ?? 100) > Number(f.winrateMax)) return false;
      if (f.trMin !== '' && (e.total_return ?? -1e9) < Number(f.trMin)) return false;
      if (f.trMax !== '' && (e.total_return ?? 1e9) > Number(f.trMax)) return false;
      if (f.sigMin !== '' && (e.sig ?? 0) < Number(f.sigMin)) return false;
      if (f.sigMax !== '' && (e.sig ?? 999) > Number(f.sigMax)) return false;
      if (f.breadthMin !== '' && (e.breadth ?? 0) < Number(f.breadthMin)) return false;
      if (f.breadthMax !== '' && (e.breadth ?? 999) > Number(f.breadthMax)) return false;
      if (f.tpMin !== '' && (e.t_p ?? -1) < Number(f.tpMin)) return false;
      if (f.tpMax !== '' && (e.t_p ?? 2) > Number(f.tpMax)) return false;
      if (f.mcpMin !== '' && (e.mc_p ?? -1) < Number(f.mcpMin)) return false;
      if (f.mcpMax !== '' && (e.mc_p ?? 2) > Number(f.mcpMax)) return false;
      if (f.kspMin !== '' && (e.ks_p ?? -1) < Number(f.kspMin)) return false;
      if (f.kspMax !== '' && (e.ks_p ?? 2) > Number(f.kspMax)) return false;
      return true;
    });
  }

  function rIn(ph, id, cb) { return $el('input', { className: 'input filter-input', placeholder: ph, id: id, oninput: cb }); }

  function buildRankFilters() {
    filterBar.innerHTML = '';
    const f = state.rankFilters;
    filterBar.append(
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Name'), rIn('Name...','rf-name',e=>{state.rankFilters.name=e.target.value.toLowerCase();refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Verdict'),
        $el('select', { className: 'form-select filter-select', id:'rf-verdict', onchange:e=>{state.rankFilters.verdict=e.target.value;refreshRank();}},
          $el('option',{value:''},'All'),$el('option',{value:'STRONG'},'STRONG'),$el('option',{value:'PASS'},'PASS'),$el('option',{value:'WEAK'},'WEAK'),$el('option',{value:'FAIL'},'FAIL'),
        ),
      ),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Score'), rIn('Min','rf-sc-min',e=>{state.rankFilters.scoreMin=e.target.value;refreshRank();}), rIn('Max','rf-sc-max',e=>{state.rankFilters.scoreMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Sharpe'), rIn('Min','rf-sh-min',e=>{state.rankFilters.sharpeMin=e.target.value;refreshRank();}), rIn('Max','rf-sh-max',e=>{state.rankFilters.sharpeMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'WinRate'), rIn('Min','rf-wr-min',e=>{state.rankFilters.winrateMin=e.target.value;refreshRank();}), rIn('Max','rf-wr-max',e=>{state.rankFilters.winrateMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'TotRet'), rIn('Min','rf-tr-min',e=>{state.rankFilters.trMin=e.target.value;refreshRank();}), rIn('Max','rf-tr-max',e=>{state.rankFilters.trMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Sig'), rIn('Min','rf-sg-min',e=>{state.rankFilters.sigMin=e.target.value;refreshRank();}), rIn('Max','rf-sg-max',e=>{state.rankFilters.sigMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Breadth'), rIn('Min','rf-br-min',e=>{state.rankFilters.breadthMin=e.target.value;refreshRank();}), rIn('Max','rf-br-max',e=>{state.rankFilters.breadthMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 't-p'), rIn('Min','rf-tp-min',e=>{state.rankFilters.tpMin=e.target.value;refreshRank();}), rIn('Max','rf-tp-max',e=>{state.rankFilters.tpMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'MC p'), rIn('Min','rf-mcp-min',e=>{state.rankFilters.mcpMin=e.target.value;refreshRank();}), rIn('Max','rf-mcp-max',e=>{state.rankFilters.mcpMax=e.target.value;refreshRank();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'KS p'), rIn('Min','rf-ksp-min',e=>{state.rankFilters.kspMin=e.target.value;refreshRank();}), rIn('Max','rf-ksp-max',e=>{state.rankFilters.kspMax=e.target.value;refreshRank();})),
    );
    // Restore filter input values from state
    const rfMap = { 'rf-name':'name','rf-verdict':'verdict','rf-sc-min':'scoreMin','rf-sc-max':'scoreMax','rf-sh-min':'sharpeMin','rf-sh-max':'sharpeMax','rf-wr-min':'winrateMin','rf-wr-max':'winrateMax','rf-tr-min':'trMin','rf-tr-max':'trMax','rf-sg-min':'sigMin','rf-sg-max':'sigMax','rf-br-min':'breadthMin','rf-br-max':'breadthMax','rf-tp-min':'tpMin','rf-tp-max':'tpMax','rf-mcp-min':'mcpMin','rf-mcp-max':'mcpMax','rf-ksp-min':'kspMin','rf-ksp-max':'kspMax' };
    Object.entries(rfMap).forEach(([id, fk]) => {
      const el = document.getElementById(id);
      if (el && state.rankFilters[fk] !== undefined) el.value = state.rankFilters[fk];
    });
  }

  function refreshRank() {
    const filtered = applyRankFilters();
    const sorted = [...filtered].sort((a, b) => {
      const c = state.rankSort.col;
      if (!c || c === '#') return 0;
      const av = a[c], bv = b[c];
      if (typeof av === 'string') return state.rankSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return state.rankSort.dir === 'asc' ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0);
    });
    _saveState();
    const tbody = document.getElementById('rank-tbody');
    const info = document.getElementById('rank-info');
    if (info) info.textContent = `${sorted.length} edges (of ${edges.length})`;
    if (tbody) {
      tbody.innerHTML = '';
      sorted.forEach((e, i) => {
        const tr = $el('tr', { className: e.verdict ? `row-${e.verdict}` : '', onclick: () => navigate(`/edges/${encodeURIComponent(e.name)}`), style: { cursor: 'pointer' } });
        tr.append($el('td', {}, String(i + 1)));
        tr.append($el('td', {}, e.name));
        tr.append($el('td', {}, e.verdict ? $el('span', { className: `badge badge-${e.verdict}` }, e.verdict) : '—'));
        tr.append($el('td', { className: 'num' }, num(e.score)));
        tr.append($el('td', { className: 'num' }, String(e.sig ?? '-')));
        tr.append($el('td', { className: 'num' }, String(e.breadth ?? '-')));
        tr.append($el('td', { className: 'num' }, num(e.sharpe)));
        tr.append($el('td', { className: 'num' }, pct(e.winrate)));
        tr.append($el('td', { className: 'num' }, num(e.total_return, 2)));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.t_p != null ? e.t_p.toFixed(3) : '-'));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.mc_p != null ? e.mc_p.toFixed(3) : '-'));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.ks_p != null ? e.ks_p.toFixed(3) : '-'));
        tbody.append(tr);
      });
    }
  }

  async function loadRanking() {
    const symbol = document.getElementById('ranking-symbol').value;
    chartDiv.innerHTML = '<div class="flex justify-center" style="padding:40px"><div class="spinner"></div></div>';
    tableDiv.innerHTML = '';
    try {
      const data = await api.get(`/api/ranking?symbol=${encodeURIComponent(symbol)}`);
      edges = data.edges || [];
      chartDiv.innerHTML = '';
      chartDiv.append($el('canvas', { id: 'ranking-chart' }));
      renderRankingChart();
      buildRankFilters();
      const table = $el('table', { className: 'data-table' },
        $el('thead', {},
          $el('tr', {},
            ...['#','Name','Verdict','Score','Sig','Breadth','Sharpe','Win Rate','Total Return','t-p','MC p','KS p'].map((k, i) => {
              const sortKeys = [null,'name','verdict','score','sig','breadth','sharpe','winrate','total_return','t_p','mc_p','ks_p'];
              const sc = sortKeys[i];
              const attrs = { className: (i >= 3 ? 'num' : '') + (state.rankSort.col === sc ? ' sorted' : ''), style: { cursor: sc ? 'pointer' : '' } };
              if (sc) attrs.onclick = () => { state.rankSort.col === sc ? (state.rankSort.dir = state.rankSort.dir === 'asc' ? 'desc' : 'asc') : (state.rankSort.col = sc, state.rankSort.dir = 'desc'); refreshRank(); };
              return $el('th', attrs, k + (state.rankSort.col === sc ? (state.rankSort.dir === 'asc' ? ' ▲' : ' ▼') : ''));
            })
          ),
        ),
        $el('tbody', { id: 'rank-tbody' }),
      );
      tableDiv.append($el('div', { id: 'rank-info', style: { fontSize: '12px', color: 'var(--text-secondary)', margin: '8px 0' } }), table);
      refreshRank();
    } catch (e) {
      chartDiv.innerHTML = `<div class="empty-state"><h3>Error loading ranking</h3><p>${e.message}</p></div>`;
    }
  }

  function renderRankingChart() {
    setTimeout(() => {
      const canvas = document.getElementById('ranking-chart');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (state.charts.ranking) { state.charts.ranking.destroy(); }
      const top25 = edges.slice(0, 25).reverse();
      const colors = top25.map(e => {
        if (e.verdict === 'STRONG') return '#3fb950';
        if (e.verdict === 'PASS') return '#58a6ff';
        if (e.verdict === 'WEAK') return '#d29922';
        return '#f85149';
      });
      state.charts.ranking = new Chart(ctx, {
        type: 'bar', data: {
          labels: top25.map(e => e.name.length > 28 ? e.name.slice(0, 28) + '…' : e.name),
          datasets: [{ data: top25.map(e => e.score || 0), backgroundColor: colors, borderColor: colors, borderWidth: 1 }]
        },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false }, tooltip: { callbacks: { label: (ctx) => { const e = top25[ctx.dataIndex]; return `Score: ${num(e.score)} | Sig: ${e.sig} | Breadth: ${e.breadth} | Sharpe: ${num(e.sharpe)}`; } } }
          },
          scales: {
            x: { grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
            y: { ticks: { color: '#8b949e', font: { size: 9 } }, grid: { display: false } }
          },
          onClick: (_, els) => { if (els.length) { const edge = edges[top25.length - 1 - els[0].datasetIndex]; if (edge) navigate(`/edges/${encodeURIComponent(edge.name)}`); } }
        }
      });
    }, 50);
  }

  // Load symbols
  try {
    const syms = await api.get('/api/symbols');
    const sel = document.getElementById('ranking-symbol');
    sel.innerHTML = '';
    syms.forEach(s => sel.append($el('option', { value: s }, s)));
  } catch (_) {}
  document.getElementById('ranking-symbol').addEventListener('change', loadRanking);
  loadRanking();
}

/* ============ OOS ============ */
async function renderOOS(container) {
  container.innerHTML = '';
  const toolbar = $el('div', { className: 'toolbar' },
    $el('select', { id: 'oos-symbol', className: 'form-select', style: { width: 'auto', minWidth: '160px' } },
      $el('option', { value: 'BTC/USDT' }, 'BTC/USDT')
    ),
    $el('button', { className: 'btn btn-primary', onclick: () => startOOS(document.getElementById('oos-symbol').value) }, 'Run OOS Validation'),
  );
  container.append(toolbar);
  const verdictDiv = $el('div', { className: 'oos-verdicts', id: 'oos-verdicts' });
  container.append(verdictDiv);
  const filterBar = $el('div', { className: 'filter-bar', id: 'oos-filter-bar' });
  container.append(filterBar);
  const tableWrap = $el('div', { className: 'table-wrap', id: 'oos-table-wrap' });
  container.append(tableWrap);

  let oosEdges = [];

  function applyOOSFilters() {
    return oosEdges.filter(e => {
      const f = state.oosFilters;
      if (f.name && !e.name.toLowerCase().includes(f.name)) return false;
      if (f.verdict && e.verdict !== f.verdict) return false;
      if (f.isScMin !== '' && (e.is_score ?? 0) < Number(f.isScMin)) return false;
      if (f.isScMax !== '' && (e.is_score ?? 100) > Number(f.isScMax)) return false;
      if (f.oosScMin !== '' && (e.oos_score ?? 0) < Number(f.oosScMin)) return false;
      if (f.oosScMax !== '' && (e.oos_score ?? 100) > Number(f.oosScMax)) return false;
      if (f.finalScMin !== '' && (e.final_score ?? 0) < Number(f.finalScMin)) return false;
      if (f.finalScMax !== '' && (e.final_score ?? 100) > Number(f.finalScMax)) return false;
      if (f.decMin !== '' && (e.decay ?? -1) < Number(f.decMin)) return false;
      if (f.decMax !== '' && (e.decay ?? 2) > Number(f.decMax)) return false;
      if (f.isShMin !== '' && (e.is_sharpe ?? -999) < Number(f.isShMin)) return false;
      if (f.isShMax !== '' && (e.is_sharpe ?? 999) > Number(f.isShMax)) return false;
      if (f.oosShMin !== '' && (e.oos_sharpe ?? -999) < Number(f.oosShMin)) return false;
      if (f.oosShMax !== '' && (e.oos_sharpe ?? 999) > Number(f.oosShMax)) return false;
      if (f.oosWrMin !== '' && (e.oos_winrate ?? 0) < Number(f.oosWrMin)) return false;
      if (f.oosWrMax !== '' && (e.oos_winrate ?? 100) > Number(f.oosWrMax)) return false;
      if (f.oosTpMin !== '' && (e.oos_t_p ?? -1) < Number(f.oosTpMin)) return false;
      if (f.oosTpMax !== '' && (e.oos_t_p ?? 2) > Number(f.oosTpMax)) return false;
      if (f.oosMcpMin !== '' && (e.oos_mc_p ?? -1) < Number(f.oosMcpMin)) return false;
      if (f.oosMcpMax !== '' && (e.oos_mc_p ?? 2) > Number(f.oosMcpMax)) return false;
      if (f.distKspMin !== '' && (e.dist_ks_p ?? -1) < Number(f.distKspMin)) return false;
      if (f.distKspMax !== '' && (e.dist_ks_p ?? 2) > Number(f.distKspMax)) return false;
      return true;
    });
  }

  function oIn(ph, id, cb) { return $el('input', { className: 'input filter-input', placeholder: ph, id: id, oninput: cb }); }

  function buildOOSFilters() {
    filterBar.innerHTML = '';
    filterBar.append(
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Name'), oIn('Name...','of-name',e=>{state.oosFilters.name=e.target.value.toLowerCase();refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Verdict'),
        $el('select', { className: 'form-select filter-select', id:'of-verdict', onchange:e=>{state.oosFilters.verdict=e.target.value;refreshOOS();}},
          $el('option',{value:''},'All'),$el('option',{value:'STRONG'},'STRONG'),$el('option',{value:'PASS'},'PASS'),$el('option',{value:'WEAK'},'WEAK'),$el('option',{value:'FAIL'},'FAIL'),
        ),
      ),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'IS Score'), oIn('Min','of-is-min',e=>{state.oosFilters.isScMin=e.target.value;refreshOOS();}), oIn('Max','of-is-max',e=>{state.oosFilters.isScMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'OOS Score'), oIn('Min','of-os-min',e=>{state.oosFilters.oosScMin=e.target.value;refreshOOS();}), oIn('Max','of-os-max',e=>{state.oosFilters.oosScMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Final Score'), oIn('Min','of-fs-min',e=>{state.oosFilters.finalScMin=e.target.value;refreshOOS();}), oIn('Max','of-fs-max',e=>{state.oosFilters.finalScMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Decay'), oIn('Min','of-de-min',e=>{state.oosFilters.decMin=e.target.value;refreshOOS();}), oIn('Max','of-de-max',e=>{state.oosFilters.decMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'IS Sharpe'), oIn('Min','of-ish-min',e=>{state.oosFilters.isShMin=e.target.value;refreshOOS();}), oIn('Max','of-ish-max',e=>{state.oosFilters.isShMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'OOS Sharpe'), oIn('Min','of-oosh-min',e=>{state.oosFilters.oosShMin=e.target.value;refreshOOS();}), oIn('Max','of-oosh-max',e=>{state.oosFilters.oosShMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'OOS WR'), oIn('Min','of-owr-min',e=>{state.oosFilters.oosWrMin=e.target.value;refreshOOS();}), oIn('Max','of-owr-max',e=>{state.oosFilters.oosWrMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'OOS t-p'), oIn('Min','of-otp-min',e=>{state.oosFilters.oosTpMin=e.target.value;refreshOOS();}), oIn('Max','of-otp-max',e=>{state.oosFilters.oosTpMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'OOS MC p'), oIn('Min','of-omp-min',e=>{state.oosFilters.oosMcpMin=e.target.value;refreshOOS();}), oIn('Max','of-omp-max',e=>{state.oosFilters.oosMcpMax=e.target.value;refreshOOS();})),
      $el('div', { className: 'filter-group' }, $el('label', {}, 'Dist KS p'), oIn('Min','of-dkp-min',e=>{state.oosFilters.distKspMin=e.target.value;refreshOOS();}), oIn('Max','of-dkp-max',e=>{state.oosFilters.distKspMax=e.target.value;refreshOOS();})),
    );
    // Restore OOS filter input values from state
    const ofMap = { 'of-name':'name','of-verdict':'verdict','of-is-min':'isScMin','of-is-max':'isScMax','of-os-min':'oosScMin','of-os-max':'oosScMax','of-fs-min':'finalScMin','of-fs-max':'finalScMax','of-de-min':'decMin','of-de-max':'decMax','of-ish-min':'isShMin','of-ish-max':'isShMax','of-oosh-min':'oosShMin','of-oosh-max':'oosShMax','of-owr-min':'oosWrMin','of-owr-max':'oosWrMax','of-otp-min':'oosTpMin','of-otp-max':'oosTpMax','of-omp-min':'oosMcpMin','of-omp-max':'oosMcpMax','of-dkp-min':'distKspMin','of-dkp-max':'distKspMax' };
    Object.entries(ofMap).forEach(([id, fk]) => {
      const el = document.getElementById(id);
      if (el && state.oosFilters[fk] !== undefined) el.value = state.oosFilters[fk];
    });
  }

  function refreshOOS() {
    const filtered = applyOOSFilters();
    const sorted = [...filtered].sort((a, b) => {
      const c = state.oosSort.col;
      if (!c) return 0;
      const av = a[c], bv = b[c];
      if (typeof av === 'string') return state.oosSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return state.oosSort.dir === 'asc' ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0);
    });
    _saveState();
    const tbody = document.getElementById('oos-tbody');
    const info = document.getElementById('oos-info');
    if (info) info.textContent = `${sorted.length} edges (of ${oosEdges.length})`;
    if (tbody) {
      tbody.innerHTML = '';
      sorted.forEach(e => {
        const tr = $el('tr', { className: e.verdict ? `row-${e.verdict}` : '', onclick: () => navigate(`/edges/${encodeURIComponent(e.name)}`), style: { cursor: 'pointer' } });
        tr.append($el('td', {}, e.name));
        tr.append($el('td', {}, e.verdict ? $el('span', { className: `badge badge-${e.verdict}` }, e.verdict) : '—'));
        tr.append($el('td', { className: 'num' }, num(e.is_score)));
        tr.append($el('td', { className: 'num' }, num(e.oos_score)));
        tr.append($el('td', { className: 'num' }, num(e.final_score)));
        tr.append($el('td', { className: 'num', style: { color: (e.decay || 0) > 0.5 ? 'var(--accent-red)' : 'var(--accent-green)' } }, pct((e.decay || 0) * 100)));
        tr.append($el('td', { className: 'num' }, num(e.is_sharpe)));
        tr.append($el('td', { className: 'num' }, num(e.oos_sharpe)));
        tr.append($el('td', { className: 'num' }, pct(e.oos_winrate)));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.oos_t_p != null ? e.oos_t_p.toFixed(3) : '-'));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.oos_mc_p != null ? e.oos_mc_p.toFixed(3) : '-'));
        tr.append($el('td', { className: 'num', style: { fontSize: '11px' } }, e.dist_ks_p != null ? e.dist_ks_p.toFixed(3) : '-'));
        tbody.append(tr);
      });
    }
  }

  async function loadOOS() {
    const symbol = document.getElementById('oos-symbol').value;
    verdictDiv.innerHTML = '<div class="flex justify-center" style="padding:20px"><div class="spinner"></div></div>';
    tableWrap.innerHTML = '';
    try {
      const data = await api.get(`/api/oos/${encodeURIComponent(symbol)}`);
      oosEdges = data.edges || [];
      verdictDiv.innerHTML = '';
      const verdicts = data.verdicts || {};
      const vData = [
        { key: 'strong', label: 'STRONG', count: verdicts.STRONG || 0, cls: 'strong' },
        { key: 'pass', label: 'PASS', count: verdicts.PASS || 0, cls: 'pass' },
        { key: 'weak', label: 'WEAK', count: verdicts.WEAK || 0, cls: 'weak' },
        { key: 'fail', label: 'FAIL', count: verdicts.FAIL || 0, cls: 'fail' },
      ];
      vData.forEach(v => {
        verdictDiv.append(
          $el('div', { className: `oos-card ${v.cls}` },
            $el('div', { className: 'count' }, String(v.count)),
            $el('div', { className: 'label' }, v.label),
          )
        );
      });
      buildOOSFilters();
      const table = $el('table', { className: 'data-table' },
        $el('thead', {},
          $el('tr', {},
            ...['Name','Verdict','IS Score','OOS Score','Final Score','Decay','IS Sharpe','OOS Sharpe','OOS WR','OOS t-p','OOS MC p','Dist KS p'].map((k, i) => {
              const sortKeys = ['name','verdict','is_score','oos_score','final_score','decay','is_sharpe','oos_sharpe','oos_winrate','oos_t_p','oos_mc_p','dist_ks_p'];
              const sc = sortKeys[i];
              const attrs = { className: (i >= 2 ? 'num' : '') + (state.oosSort.col === sc ? ' sorted' : ''), style: { cursor: sc ? 'pointer' : '' } };
              if (sc) attrs.onclick = () => { state.oosSort.col === sc ? (state.oosSort.dir = state.oosSort.dir === 'asc' ? 'desc' : 'asc') : (state.oosSort.col = sc, state.oosSort.dir = 'desc'); refreshOOS(); };
              return $el('th', attrs, k + (state.oosSort.col === sc ? (state.oosSort.dir === 'asc' ? ' ▲' : ' ▼') : ''));
            })
          ),
        ),
        $el('tbody', { id: 'oos-tbody' }),
      );
      tableWrap.append($el('div', { id: 'oos-info', style: { fontSize: '12px', color: 'var(--text-secondary)', margin: '8px 0' } }), table);
      refreshOOS();
    } catch (e) {
      verdictDiv.innerHTML = `<div class="empty-state"><h3>Error loading OOS data</h3><p>${e.message}</p></div>`;
    }
  }

  try {
    const syms = await api.get('/api/symbols');
    const sel = document.getElementById('oos-symbol');
    sel.innerHTML = '';
    syms.forEach(s => sel.append($el('option', { value: s }, s)));
    sel.value = state.oosSymbol || 'BTC/USDT';
  } catch (_) {}
  document.getElementById('oos-symbol').addEventListener('change', () => {
    state.oosSymbol = document.getElementById('oos-symbol').value;
    _saveState();
    loadOOS();
  });
  loadOOS();
}

/* ============ CREATE EDGE ============ */
async function renderCreateEdge(container) {
  container.innerHTML = '';
  let indicators = [];
  try {
    const indData = await api.get('/api/indicators');
    indicators = indData.categories || {};
  } catch (_) {}

  const indPanel = $el('div', { className: 'card', style: { marginTop: '12px', display: 'none' }, id: 'ind-ref-panel' },
    $el('h3', { style: { marginTop: 0 } }, 'Available Indicators'),
    $el('div', { id: 'ind-ref-content', style: { maxHeight: '300px', overflowY: 'auto', fontSize: '13px', columns: '3 200px' } }),
  );

  const form = $el('form', { className: 'card', style: { maxWidth: '680px' }, onsubmit: (e) => e.preventDefault() },
    $el('div', { className: 'form-group' },
      $el('label', {}, 'Name'),
      $el('input', { className: 'form-input', id: 'create-name', placeholder: 'e.g. RSI 14 oversold <25', required: true }),
    ),
    $el('div', { className: 'form-group' },
      $el('label', {}, 'Long Formula'),
      $el('textarea', { className: 'form-input', id: 'create-long', placeholder: 'e.g. rsi(close, 14) < 25', rows: 3, required: true }),
      $el('div', { className: 'help-text' }, 'See indicator reference below. Use: rsi(close,14), sma(close,20), bb_lower(close,20,2), close > ema(close,50)'),
    ),
    $el('div', { className: 'form-group' },
      $el('label', {}, 'Short Formula'),
      $el('textarea', { className: 'form-input', id: 'create-short', placeholder: 'e.g. rsi(close, 14) > 75', rows: 3 }),
      $el('div', { className: 'help-text' }, 'Optional — leave empty for long-only edges'),
    ),
    $el('div', { className: 'form-group' },
      $el('label', {}, 'Horizons'),
      $el('input', { className: 'form-input', id: 'create-horizons', value: '1,4,6,12,24,48,72,168' }),
      $el('div', { className: 'help-text' }, 'Comma-separated list of hour horizons'),
    ),
    $el('div', { className: 'form-group' },
      $el('label', {}, 'Description'),
      $el('textarea', { className: 'form-input', id: 'create-desc', placeholder: 'Describe the edge logic...', rows: 2 }),
    ),
    $el('button', { className: 'btn btn-link', style: { marginBottom: '12px', fontSize: '13px', cursor: 'pointer', background: 'none', border: 'none', color: 'var(--accent-blue)', padding: '0' }, onclick: (e) => {
      e.preventDefault();
      const p = document.getElementById('ind-ref-panel');
      const content = document.getElementById('ind-ref-content');
      if (p.style.display === 'none') {
        p.style.display = 'block';
        if (!content.children.length) {
          let html = '';
          Object.entries(indicators).forEach(([cat, names]) => {
            html += `<div style="break-inside:avoid;margin-bottom:8px"><strong style="color:var(--accent-blue)">${cat}</strong><br>`;
            names.forEach(n => { html += `<code style="font-size:12px;color:var(--text-secondary)">${n}</code> `; });
            html += '</div>';
          });
          content.innerHTML = html;
        }
      } else { p.style.display = 'none'; }
    } }, 'Toggle indicator reference'),
    $el('div', { id: 'create-error', className: 'error-text', style: { display: 'none', marginBottom: '12px' } }),
    $el('button', { className: 'btn btn-success', id: 'create-btn', onclick: handleCreate }, 'Create & Validate'),
  );
  container.append(form);
  container.append(indPanel);
  // Pre-populate indicator reference
  const content = document.getElementById('ind-ref-content');
  if (content) {
    let html = '';
    Object.entries(indicators).forEach(([cat, names]) => {
      html += `<div style="break-inside:avoid;margin-bottom:8px"><strong style="color:var(--accent-blue)">${cat}</strong><br>`;
      names.forEach(n => { html += `<code style="font-size:12px;color:var(--text-secondary)">${n}</code> `; });
      html += '</div>';
    });
    content.innerHTML = html;
  }

  async function handleCreate() {
    const name = document.getElementById('create-name').value.trim();
    const long = document.getElementById('create-long').value.trim();
    const short = document.getElementById('create-short').value.trim();
    const horizons = document.getElementById('create-horizons').value.trim();
    const desc = document.getElementById('create-desc').value.trim();
    const err = document.getElementById('create-error');
    const btn = document.getElementById('create-btn');

    if (!name || !long) { err.textContent = 'Name and Long Formula are required'; err.style.display = 'block'; return; }
    err.style.display = 'none';
    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
      const result = await api.post('/api/edges/create', { name, long_formula: long, short_formula: short, horizons, description: desc });
      btn.disabled = false;
      btn.textContent = 'Create & Validate';
      const encoded = encodeURIComponent(name);
      // Success modal
      const modal = $el('div', { className: 'modal-overlay', onclick: (e) => { if (e.target === modal) modal.remove(); } },
        $el('div', { className: 'modal' },
          $el('div', { className: 'modal-title' }, 'Edge Created'),
          $el('div', { className: 'modal-body' }, `"${name}" has been created successfully.`),
          $el('div', { className: 'modal-actions' },
            $el('button', { className: 'btn btn-primary', onclick: () => { modal.remove(); navigate(`/edges/${encoded}`); } }, 'View Edge'),
            $el('button', { className: 'btn', onclick: () => modal.remove() }, 'Close'),
          ),
        )
      );
      document.body.appendChild(modal);
    } catch (e) {
      err.textContent = e.message;
      err.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Create & Validate';
    }
  }
}

/* ============ ANALYSIS / OOS TRIGGER ============ */
function startAnalysis(edgeNames, force = false, quick = false, symbols = null) {
  const names = Array.isArray(edgeNames) ? edgeNames : null;
  if (symbols == null) {
    symbols = state.dashboardSymbols.length > 0 ? state.dashboardSymbols : [state.symbol || 'BTC/USDT'];
  }
  const symbolsStr = symbols.join(',');
  const label = names ? `Analyzing ${names.length} edge(s)` : `Analyzing all edges (${symbols.length} symbol(s))`;
  showProgress(label, names ? names.length : 0);

  api.post('/api/analyze', {
    symbol: symbols[0],
    symbols: symbolsStr,
    edge_name: names && names.length === 1 ? names[0] : null,
    quick,
    force,
    since: '2020-01-01',
    until: '2026-06-13'
  }).then(resp => {
    try { sessionStorage.setItem('active_task', JSON.stringify({ url: `/api/analyze/${resp.task_id}/progress`, type: 'analyze' })); } catch (_) {}
    connectSSE(`/api/analyze/${resp.task_id}/progress`, null, () => {
      try { sessionStorage.removeItem('active_task'); } catch (_) {}
      const route = getRoute();
      if (route.page === 'edge-detail') {
        const container = document.getElementById('main-content');
        renderEdgeDetail(container, route.name);
      } else if (route.page === 'edges') {
        const container = document.getElementById('main-content');
        renderEdgeList(container);
      }
    });
  }).catch(e => {
    hideProgress();
    toast(`Error: ${e.message}`, 'error');
  });
}

function startOOS(symbol) {
  showProgress('Running OOS Validation', 100);
  api.post('/api/oos-validate', { symbol, since: '2020-01-01', until: '2026-06-13' }).then(resp => {
    try { sessionStorage.setItem('active_task', JSON.stringify({ url: `/api/oos-validate/${resp.task_id}/progress`, type: 'oos' })); } catch (_) {}
    connectSSE(`/api/oos-validate/${resp.task_id}/progress`, null, () => {
      try { sessionStorage.removeItem('active_task'); } catch (_) {}
      const route = getRoute();
      if (route.page === 'oos') {
        const container = document.getElementById('main-content');
        renderOOS(container);
      }
    });
  }).catch(e => {
    hideProgress();
    toast(`Error: ${e.message}`, 'error');
  });
}

/* ============ INIT ============ */
document.addEventListener('DOMContentLoaded', () => {
  // Create progress bar
  const progressBar = $el('div', { id: 'progress-bar', className: 'progress-bar-fixed' },
    $el('div', { className: 'progress-info' },
      $el('span', { id: 'progress-label', className: 'progress-label' }, ''),
      $el('span', { id: 'progress-stats', className: 'progress-stats' }, ''),
    ),
    $el('div', { className: 'progress-info' },
      $el('span', { id: 'progress-elapsed', style: { fontSize: '11px', color: 'var(--text-secondary)' } }, ''),
    ),
    $el('div', { className: 'progress-track' },
      $el('div', { id: 'progress-fill', className: 'progress-fill' }),
    ),
  );
  document.body.appendChild(progressBar);

  // Toast container
  const toastContainer = $el('div', { id: 'toast-container', className: 'toast-container' });
  document.body.appendChild(toastContainer);

  // Reconnect active task on page refresh
  try {
    const active = JSON.parse(sessionStorage.getItem('active_task'));
    if (active && active.url) {
      state.currentTask = { label: 'Reconnecting...', total: 0, completed: 0, skipped: 0, failed: 0, start: Date.now() };
      const bar = document.getElementById('progress-bar');
      bar.classList.add('visible');
      updateProgress();
      // Try to reconnect — first progress event updates total/label
      connectSSE(active.url, null, () => {
        try { sessionStorage.removeItem('active_task'); } catch (_) {}
        hideProgress();
      });
    }
  } catch (_) {}

  renderApp();
});
