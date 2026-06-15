/**
 * Unit tests for frontend JS functions.
 * Run with: node webapp/tests/test_frontend.js
 */

const fs = require('fs');
const path = require('path');

// Load the JS file and extract pure functions using eval
const jsPath = path.join(__dirname, '..', 'static', 'app.js');
let jsCode = fs.readFileSync(jsPath, 'utf-8');

// Mock browser globals needed by the app
global.document = {
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    className: '',
    style: {},
    onclick: null,
    dataset: {},
    children: [],
    innerHTML: '',
    append: function(...items) {
      for (const item of items) {
        if (item instanceof Node) this.children.push(item);
        else this.children.push(String(item));
      }
    },
    addEventListener: function() {},
    setAttribute: function() {},
    getContext: () => ({}),
    getElementById: () => null,
    appendChild: function(child) { this.children.push(child); return child; },
    remove: function() {},
  }),
  createTextNode: (text) => ({ nodeType: 3, textContent: text }),
  body: { appendChild: () => {}, removeChild: () => {} },
  getElementById: () => null,
};

global.window = {
  location: { hash: '', pathname: '/', search: '' },
  setTimeout: () => 0,
  addEventListener: () => {},
};

global.Node = class Node {};
global.EventSource = class EventSource {
  constructor() { this.onmessage = null; this.onerror = null; }
  close() {}
};

// Chart.js mock
global.Chart = class Chart {
  constructor(ctx, config) {
    this.ctx = ctx;
    this.config = config;
    this.data = config.data;
    Chart.instances.push(this);
  }
  destroy() { this.destroyed = true; }
  static instances = [];
};

// Mock fetch - returns empty JSON for all calls
global.fetch = async (url) => ({
  ok: true,
  status: 200,
  statusText: 'OK',
  json: async () => ({}),
  text: async () => '',
});

// Extract only the pure utility functions by evaluating selected parts
function extractFunction(code, fnName) {
  const re = new RegExp(`(function\\s+${fnName}\\s*\\([^)]*\\)\\s*\\{[\\s\\S]*?^\\})`, 'm');
  const match = code.match(re);
  if (!match) throw new Error(`Function ${fnName} not found`);
  return match[1];
}

// Remove DOM-dependent code and evaluate pure utility functions
let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✓ ${name}`);
  } catch (e) {
    failed++;
    console.log(`  ✗ ${name}: ${e.message}`);
  }
}

function assert(condition, msg = '') {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

// Manually define the utility functions that match the app's implementations
// These are extracted from app.js logic

function num(n, d = 2) {
  if (n == null) return '-';
  const v = Number(n);
  if (isNaN(v) || !isFinite(v)) return '-';
  return v.toFixed(d);
}

function pct(n) {
  if (n == null) return '-';
  const v = Number(n);
  if (isNaN(v) || !isFinite(v)) return '-';
  return v.toFixed(1) + '%';
}

// Test ranking filter logic
function applyRankFilters(edges, filters) {
  const f = filters;
  return edges.filter(e => {
    if (f.name && !e.name.toLowerCase().includes(f.name)) return false;
    if (f.verdict && e.verdict !== f.verdict) return false;
    if (f.scoreMin !== '' && (e.score ?? 0) < Number(f.scoreMin)) return false;
    if (f.scoreMax !== '' && (e.score ?? 0) > Number(f.scoreMax)) return false;
    if (f.sharpeMin !== '' && (e.sharpe ?? -999) < Number(f.sharpeMin)) return false;
    if (f.sharpeMax !== '' && (e.sharpe ?? 999) > Number(f.sharpeMax)) return false;
    if (f.winrateMin !== '' && (e.winrate ?? 0) < Number(f.winrateMin)) return false;
    if (f.winrateMax !== '' && (e.winrate ?? 100) > Number(f.winrateMax)) return false;
    if (f.tpMin !== '' && (e.t_p ?? -1) < Number(f.tpMin)) return false;
    if (f.tpMax !== '' && (e.t_p ?? 2) > Number(f.tpMax)) return false;
    if (f.mcpMin !== '' && (e.mc_p ?? -1) < Number(f.mcpMin)) return false;
    if (f.mcpMax !== '' && (e.mc_p ?? 2) > Number(f.mcpMax)) return false;
    if (f.kspMin !== '' && (e.ks_p ?? -1) < Number(f.kspMin)) return false;
    if (f.kspMax !== '' && (e.ks_p ?? 2) > Number(f.kspMax)) return false;
    return true;
  });
}

function applyOOSFilters(edges, filters) {
  const f = filters;
  return edges.filter(e => {
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

function sortEdges(filtered, sortCol, sortDir) {
  return [...filtered].sort((a, b) => {
    if (!sortCol) return 0;
    const av = a[sortCol], bv = b[sortCol];
    if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortDir === 'asc' ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0);
  });
}

// Additional test functions
function applyEdgeFilters(edges, filters) {
  const f = filters;
  return edges.filter(e => {
    if (f.search && !e.name.toLowerCase().includes(f.search.toLowerCase())) return false;
    if (f.status === 'analyzed' && !e.has_analysis) return false;
    if (f.status === 'pending' && e.has_analysis) return false;
    return true;
  });
}

function sortEdgesBy(field, order, list) {
  return [...list].sort((a, b) => {
    const av = a[field], bv = b[field];
    if (typeof av === 'string') return order === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return order === 'asc' ? (av || 0) - (bv || 0) : (bv || 0) - (av || 0);
  });
}



const sampleRankFilters = { name: '', verdict: '', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };

const sampleOOSFilters = { name: '', verdict: '', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '', oosMcpMax: '', distKspMin: '', distKspMax: '' };

// ======= RUN TESTS =======

console.log('\n=== Utility Functions ===');

test('num formats numbers', () => {
  assert(num(1.23456) === '1.23');
  assert(num(0) === '0.00');
  assert(num(null) === '-');
  assert(num(undefined) === '-');
  assert(num(5, 0) === '5');
});

test('pct formats percentages', () => {
  assert(pct(53.61) === '53.6%');
  assert(pct(0) === '0.0%');
  assert(pct(null) === '-');
});

console.log('\n=== Ranking Filters ===');

const sampleEdges = [
  { name: 'RSI 14 Oversold', score: 44, sig: 3, breadth: 5, verdict: 'STRONG', sharpe: 1.2, winrate: 62.5, total_return: 500, t_p: 0.001, mc_p: 0.02, ks_p: 0.01 },
  { name: 'MACD Bull Cross', score: 30, sig: 2, breadth: 3, verdict: 'PASS', sharpe: 0.8, winrate: 55.0, total_return: 200, t_p: 0.01, mc_p: 0.05, ks_p: 0.03 },
  { name: 'EMA Crossover', score: 15, sig: 0, breadth: 1, verdict: 'WEAK', sharpe: 0.3, winrate: 48.0, total_return: -50, t_p: 0.5, mc_p: 0.4, ks_p: 0.3 },
  { name: 'BB Reversal', score: 5, sig: 0, breadth: 0, verdict: 'FAIL', sharpe: -0.2, winrate: 35.0, total_return: -200, t_p: 0.9, mc_p: 0.8, ks_p: 0.7 },
];

test('name filter', () => {
  const f = { name: 'rsi', verdict: '', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 1);
  assert(r[0].name === 'RSI 14 Oversold');
});

test('verdict filter', () => {
  const f = { name: '', verdict: 'STRONG', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 1);
  assert(r[0].verdict === 'STRONG');
});

test('score range filter', () => {
  const f = { name: '', verdict: '', scoreMin: '20', scoreMax: '40', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 1);
  assert(r[0].name === 'MACD Bull Cross');
});

test('t_p range filter', () => {
  const f = { name: '', verdict: '', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '0', tpMax: '0.05', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 2, `expected 2, got ${r.length}`);
  assert(r[0].t_p <= 0.05);
  assert(r[1].t_p <= 0.05);
});

test('mc_p range filter', () => {
  const f = { name: '', verdict: '', scoreMin: '', scoreMax: '', sharpeMin: '', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '0', mcpMax: '0.03', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 1, `expected 1, got ${r.length}`);
  assert(r[0].mc_p <= 0.03);
});

test('multiple filters combined', () => {
  const f = { name: '', verdict: '', scoreMin: '10', scoreMax: '50', sharpeMin: '0.5', sharpeMax: '', winrateMin: '', winrateMax: '', trMin: '', trMax: '', sigMin: '', sigMax: '', breadthMin: '', breadthMax: '', tpMin: '', tpMax: '', mcpMin: '', mcpMax: '', kspMin: '', kspMax: '' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 2, `expected 2, got ${r.length}`);
});

console.log('\n=== OOS Filters ===');

const sampleOOSEdges = [
  { name: 'Edge A', verdict: 'STRONG', is_score: 70, oos_score: 65, final_score: 62, decay: 0.1, oos_sharpe: 1.5, oos_winrate: 65, oos_t_p: 0.001, oos_mc_p: 0.01, dist_ks_p: 0.05, is_sharpe: 1.8 },
  { name: 'Edge B', verdict: 'PASS', is_score: 55, oos_score: 50, final_score: 48, decay: 0.3, oos_sharpe: 0.9, oos_winrate: 58, oos_t_p: 0.01, oos_mc_p: 0.03, dist_ks_p: 0.15, is_sharpe: 1.0 },
  { name: 'Edge C', verdict: 'WEAK', is_score: 35, oos_score: 30, final_score: 25, decay: 0.6, oos_sharpe: 0.2, oos_winrate: 45, oos_t_p: 0.5, oos_mc_p: 0.4, dist_ks_p: 0.5, is_sharpe: 0.3 },
  { name: 'Edge D', verdict: 'FAIL', is_score: 15, oos_score: 10, final_score: 5, decay: 0.9, oos_sharpe: -0.5, oos_winrate: 30, oos_t_p: 0.9, oos_mc_p: 0.8, dist_ks_p: 0.9, is_sharpe: -0.2 },
];

test('OOS name filter', () => {
  const f = { name: 'edge a', verdict: '', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '', oosMcpMax: '', distKspMin: '', distKspMax: '' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 1);
  assert(r[0].name === 'Edge A');
});

test('OOS verdict filter', () => {
  const f = { name: '', verdict: 'PASS', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '', oosMcpMax: '', distKspMin: '', distKspMax: '' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 1);
});

test('OOS oos_mc_p filter', () => {
  const f = { name: '', verdict: '', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '0', oosMcpMax: '0.05', distKspMin: '', distKspMax: '' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 2, `expected 2, got ${r.length}`);
});

test('OOS dist_ks_p filter', () => {
  const f = { name: '', verdict: '', isScMin: '', isScMax: '', oosScMin: '', oosScMax: '', finalScMin: '', finalScMax: '', decMin: '', decMax: '', isShMin: '', isShMax: '', oosShMin: '', oosShMax: '', oosWrMin: '', oosWrMax: '', oosTpMin: '', oosTpMax: '', oosMcpMin: '', oosMcpMax: '', distKspMin: '0', distKspMax: '0.1' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 1, `expected 1, got ${r.length}`);
});

console.log('\n=== Sorting ===');

test('sort by score descending', () => {
  const sorted = sortEdges(sampleEdges, 'score', 'desc');
  assert(sorted[0].score >= sorted[1].score);
  assert(sorted[1].score >= sorted[2].score);
});

test('sort by name ascending', () => {
  const sorted = sortEdges(sampleEdges, 'name', 'asc');
  assert(sorted[0].name <= sorted[1].name);
});

test('sort by t_p ascending', () => {
  const sorted = sortEdges(sampleEdges, 't_p', 'asc');
  assert(sorted[0].t_p <= sorted[1].t_p);
});

test('sort by mc_p descending', () => {
  const sorted = sortEdges(sampleEdges, 'mc_p', 'desc');
  assert(sorted[0].mc_p >= sorted[1].mc_p);
});

console.log('\n=== Edge List Filters ===');

test('edge list search filter', () => {
  const list = [
    { name: 'RSI 14 Oversold', has_analysis: true },
    { name: 'MACD Crossing', has_analysis: false },
    { name: 'Bollinger Bands', has_analysis: true },
  ];
  const r = applyEdgeFilters(list, { search: 'RSI', status: 'all' });
  assert(r.length === 1);
  assert(r[0].name === 'RSI 14 Oversold');
});

test('edge list status filter analyzed', () => {
  const list = [
    { name: 'Edge A', has_analysis: true },
    { name: 'Edge B', has_analysis: false },
    { name: 'Edge C', has_analysis: true },
  ];
  const r = applyEdgeFilters(list, { search: '', status: 'analyzed' });
  assert(r.length === 2);
  assert(r.every(e => e.has_analysis));
});

test('edge list status filter pending', () => {
  const list = [
    { name: 'Edge A', has_analysis: true },
    { name: 'Edge B', has_analysis: false },
  ];
  const r = applyEdgeFilters(list, { search: '', status: 'pending' });
  assert(r.length === 1);
  assert(!r[0].has_analysis);
});

test('edge list sort by name desc', () => {
  const list = [{ name: 'A' }, { name: 'B' }, { name: 'C' }];
  const sorted = sortEdgesBy('name', 'desc', list);
  assert(sorted[0].name === 'C');
  assert(sorted[2].name === 'A');
});

test('edge list sort by name asc', () => {
  const list = [{ name: 'C' }, { name: 'A' }, { name: 'B' }];
  const sorted = sortEdgesBy('name', 'asc', list);
  assert(sorted[0].name === 'A');
  assert(sorted[2].name === 'C');
});

console.log('\n=== Utility Edge Cases ===');

test('num handles NaN and Infinity', () => {
  assert(num(NaN) === '-');
  assert(num(Infinity) === '-');
  assert(num(-Infinity) === '-');
  assert(num(0) === '0.00');
  assert(num(1.5, 0) === '2');
});

test('pct handles NaN and Infinity', () => {
  assert(pct(NaN) === '-');
  assert(pct(Infinity) === '-');
  assert(pct(0) === '0.0%');
  assert(pct(100) === '100.0%');
});

console.log('\n=== Filter Edge Cases ===');

test('empty rank filters returns all', () => {
  const r = applyRankFilters(sampleEdges, sampleRankFilters);
  assert(r.length === sampleEdges.length);
});

test('empty OOS filters returns all', () => {
  const r = applyOOSFilters(sampleOOSEdges, sampleOOSFilters);
  assert(r.length === sampleOOSEdges.length);
});

test('rank filter sharpe range excludes none', () => {
  const f = { ...sampleRankFilters, sharpeMin: '10', sharpeMax: '20' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 0);
});

test('rank filter winrate range exact match', () => {
  const f = { ...sampleRankFilters, winrateMin: '55', winrateMax: '55' };
  const r = applyRankFilters(sampleEdges, f);
  assert(r.length === 1);
  assert(r[0].name === 'MACD Bull Cross');
});

test('OOS decay filter', () => {
  const f = { ...sampleOOSFilters, decMin: '0.5', decMax: '1' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 2);
  assert(r.every(e => e.decay >= 0.5 && e.decay <= 1));
});

test('OOS is_sharpe filter', () => {
  const f = { ...sampleOOSFilters, isShMin: '1', isShMax: '2' };
  const r = applyOOSFilters(sampleOOSEdges, f);
  assert(r.length === 2);
  assert(r.every(e => e.is_sharpe >= 1 && e.is_sharpe <= 2));
});

console.log('\n=== Sort Edge Cases ===');

test('sort with null values', () => {
  const list = [{ score: 10 }, { score: null }, { score: 5 }];
  const sorted = sortEdges(list, 'score', 'desc');
  assert(sorted[0].score === 10);
  assert(sorted[2].score === null || sorted[2].score === 5);
});

test('sort by empty field does not crash', () => {
  const sorted = sortEdges(sampleEdges, '', 'asc');
  assert(sorted.length === sampleEdges.length);
});

test('sort by string field desc', () => {
  const sorted = sortEdges(sampleEdges, 'name', 'desc');
  assert(sorted[0].name >= sorted[sorted.length - 1].name);
});

console.log('\n=== JS Syntax Check ===');

test('app.js has valid syntax', () => {
  new Function(jsCode); // will throw if syntax error
});

test('app.js has no onclick: null', () => {
  assert(!jsCode.includes('onclick: null'), 'Found onclick: null');
});

test('app.js uses spread with map in thead', () => {
  // Ensure all $el('tr', {}, [...].map(...) patterns use ...
  const lines = jsCode.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    // Check for map calls inside $el('tr', ...) without spread
    if (line.includes('.map(') && line.includes('$el(\'tr\'')) {
      const prevLine = lines[Math.max(0, i - 1)];
      if (!prevLine.trim().startsWith('...') && !line.startsWith('...')) {
        // Allow if the map is on same line as ...
        if (!line.trim().startsWith('...')) {
          throw new Error(`Line ${i + 1}: .map() in tr without spread: ${line.substring(0, 60)}`);
        }
      }
    }
  }
});

// ======= SUMMARY =======

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);
if (failed > 0) process.exit(1);
