# Edge Generator — Web Application Specification

## Architecture

```
webapp/
├── server.py                  # FastAPI backend (single-file, < 500 lines)
├── templates/
│   └── index.html             # SPA frontend (single-file, ~500-800 lines)
├── static/
│   ├── app.css                # CSS (dark theme, animations)
│   └── app.js                 # Vanilla JS SPA logic (~600-900 lines)
├── cache/                     # Cached candles (shared with CLI)
├── reports/                   # Shared analysis reports (JSON + PNG)
├── reports_BTC_USDT/          # Existing reports (read-only reference)
├── reports_DOGE_USDT/         # Existing reports (read-only reference)
├── oos_BTC_USDT.txt           # Existing OOS reports
├── oos_BTC_USDT.csv
├── edge_ranking_BTC_USDT.png  # Existing rankings
└── SPEC.md                    # This document
```

**No external database.** The Edge registry (`edge_registry.py`) is in-memory and populated from `edges/*.py` files at startup. Reports are filesystem-based (JSON + PNG per edge, already existing).

## Backend (FastAPI, Python)

### Startup

1. Register example edges via `register_example_edges()`
2. Load user edges via `load_user_edges()` — scans `edges/*.py`
3. Scan existing reports directories to know which edges already have results

### Async Task Management

For long-running operations (analyze all 1200 edges, OOS validation), use:
- **`concurrent.futures.ProcessPoolExecutor`** + asyncio
- **SSE (Server-Sent Events)** endpoint for progress streaming
- A simple `dict` of active tasks with progress state

Each edge analysis sends an SSE message on completion:
```json
{"type": "progress", "edge_name": "...", "completed": 45, "total": 1200, "status": "done|skip|fail", "elapsed": 0.5}
```

On completion of all edges, sends:
```json
{"type": "complete", "total": 1200, "completed": 1195, "skipped": 3, "failed": 2, "elapsed": 45.2}
```

Progress is updated via `multiprocessing` callbacks — each worker writes to a shared `multiprocessing.Manager.dict()` for progress, and the main thread polls it and pushes SSE updates.

### API Endpoints

#### `GET /api/edges`
List all registered edges with optional filtering.

**Query params:** `?search=RSI&sort=name&order=asc&page=1&per_page=50&status=all|analyzed|pending`
**Response:**
```json
{
  "total": 1193,
  "page": 1,
  "per_page": 50,
  "edges": [
    {
      "name": "RSI 14 oversold <25",
      "description": "RSI en zone extreme...",
      "signal_type": "long",
      "has_analysis": true,
      "verdict": "STRONG",
      "best_sharpe": 1.23,
      "best_winrate": 62.5,
      "total_signals": 234,
      "report_json": "/api/report/RSI_14_oversold_<25",
      "report_png": "/api/report/RSI_14_oversold_<25/png"
    }
  ]
}
```

Edge list comes from `_registry` but `has_analysis`, `verdict`, etc come from scanning existing `reports_{SYMBOL}/` directories and reading `analysis.json` files.

The `status` filter:
- `all` — show all edges
- `analyzed` — only edges with existing analysis.json
- `pending` — only edges without analysis

#### `GET /api/indicators`
Returns all available indicators with categories.

**Response:**
```json
{
  "total": 95,
  "categories": {
    "Trend": ["sma", "ema", "wma", ...],
    "Momentum": ["rsi", "macd", ...],
    ...
  }
}
```

#### `GET /api/edges/{name}`
**Response:** Same JSON as `_build_analysis_json()` returns — all horizon stats, persistence, tests, source file, report image URL.

#### `GET /api/report/{name}/json`
Returns the raw `analysis.json` file content for the edge (from the reports directory).

#### `GET /api/report/{name}/png`
Returns the `report.png` file for the edge (from the reports directory). Returns 404 if not found.

#### `GET /api/ranking?symbol=BTC/USDT`
Returns ranking data (from pre-computed analysis.json files).

**Response:**
```json
{
  "edges": [
    {"name": "...", "score": 45.2, "sig": 18, "breadth": 5, "sharpe": 1.2, "winrate": 65, "total_return": 12.5},
    ...
  ],
  "ranking_png": "/api/ranking/BTC_USDT/png"
}
```

#### `GET /api/ranking/{symbol}/png`
Returns the ranking chart PNG.

#### `GET /api/oos/{symbol}`
Returns OOS validation results.

**Response:**
```json
{
  "verdicts": {"STRONG": 2, "PASS": 33, "WEAK": 1024, "FAIL": 140},
  "edges": [
    {"name": "...", "verdict": "STRONG", "is_score": 85, "oos_score": 72, "decay": 0.15},
    ...
  ]
}
```

#### `GET /api/symbols`
Returns available trading pairs that have reports.

```json
["BTC/USDT", "DOGE/USDT"]
```

#### `POST /api/analyze`
Start async analysis of one or all edges.

**Request body:**
```json
{
  "symbol": "BTC/USDT",
  "since": "2020-01-01",
  "until": "2026-06-13",
  "edge_name": "RSI 14 oversold <25",
  "quick": true
}
```

If `edge_name` is null or empty, run all edges. If set, run just that one.

**Response (immediate):**
```json
{"task_id": "abc123", "status": "started", "estimated_total": 1200}
```

Progress streamed via SSE at `GET /api/analyze/{task_id}/progress`.

#### `GET /api/analyze/{task_id}/progress`
SSE endpoint. Streams progress events:
```
event: progress
data: {"type": "progress", "edge_name": "...", "completed": 45, "total": 1200, "status": "done", "elapsed": 1.2}

event: complete
data: {"type": "complete", "total": 1200, "completed": 1195, "skipped": 3, "failed": 2, "elapsed": 45.2}
```

#### `POST /api/oos-validate`
Start async OOS validation.

**Request body:**
```json
{
  "symbol": "BTC/USDT",
  "since": "2020-01-01",
  "until": "2026-06-13"
}
```

Same SSE progress pattern. Endpoint: `GET /api/oos-validate/{task_id}/progress`.

#### `POST /api/edges/create`
Create a new edge.

**Request body:**
```json
{
  "name": "My Custom Edge",
  "long_formula": "rsi(close, 14) < 25",
  "short_formula": "rsi(close, 14) > 75",
  "horizons": "1,4,6,12,24,48,72,168",
  "description": "Mean reversion RSI"
}
```

**Response:** `{"status": "created", "filepath": "edges/my_custom_edge.py"}`

## Frontend (Vanilla JS SPA)

### Technology Choices
- **Vanilla JS** (no React/Vue — keeps it light and fast)
- **Chart.js** for interactive charts (ranking bars, horizon stats, equity curves)
- **CSS custom properties** for dark theme, CSS transitions/animations
- **Fetch API** for all backend calls
- **EventSource** for SSE progress streaming

### Pages / Views (SPA with hash routing)

#### 1. Dashboard (`#/`)
- Summary cards: total edges, analyzed, pending, symbols
- Quick actions: "Analyze All", "View Ranking", "OOS Validation"
- Last analysis summary (if any)
- Tiny sparkline-style stats

#### 2. Edge List (`#/edges`)
- Table with columns: Name, Signal Type, Verdict, Sharpe, Win Rate, Signals, Actions
- Search bar (live filter as you type)
- Column sorting (click header)
- Symbol selector (dropdown: BTC/USDT, DOGE/USDT)
- Status filter: All / Analyzed / Pending
- Pagination (50 per page)
- Select checkboxes → multi-select actions: "Run Analysis", "Compare"
- Progress bar at top when analysis is running (persistent across navigation)

#### 3. Edge Detail (`#/edges/{name}`)
- Header: Name, description, source file link
- Verdict badge (STRONG=green, MODERATE=yellow, WEAK=orange, NONE=red)
- **Horizon stats table**: each row = one horizon, columns = n_signals, mean %, winrate %, sharpe, t_p, mc_p, total_return
- **Equity curve chart** (line chart, all horizons overlaid, 8 lines with different colors + legend)
- **Stat bars**: Sharpe, Win Rate, Mean Return (bar chart comparing horizons)
- **Report PNG** (if available, displayed as image)
- **Raw JSON** toggle (expandable collapsible section)
- Action buttons: "Re-run Analysis", "View in Ranking"

#### 4. Ranking (`#/ranking`)
- Interactive horizontal bar chart (top 40 edges by score)
- Color-coded by verdict
- Hover tooltip with edge name, score, sharpe, winrate
- Click bar → go to edge detail
- Symbol selector
- Loading state while computing

#### 5. OOS Validation (`#/oos`)
- Summary cards: STRONG count (green), PASS count (blue), WEAK count (orange), FAIL count (red)
- Table of all edges with verdict, IS score, OOS score, decay %
- Color-coded rows by verdict
- Sort columns
- Symbol selector
- Button to run OOS validation (with progress)

#### 6. Create Edge (`#/create`)
- Form: Name, Long formula, Short formula, Horizons (comma-separated, pre-filled with `1,4,6,12,24,48,72,168`), Description
- Live formula validation (call `/api/indicators` on load, show autocomplete suggestions)
- "Create & Validate" button
- Success → redirect to edge detail (analysis pending)
- Error → show validation error message

### Progress Bar System
- **Global top bar** (fixed position) appears when any async task is running
- Shows: task description, progress percentage, elapsed time, completed/skipped/failed counts
- Smooth animation (CSS transition on width)
- Each new completed edge triggers a mini "toast" notification: "✅ RSI 14 oversold done"
- On completion: summary toast with total counts + time

### Dark Theme
```css
:root {
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-card: #1c2333;
  --bg-hover: #252d3f;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --accent-yellow: #d29922;
  --accent-red: #f85149;
  --accent-orange: #d4760a;
  --border: #30363d;
  --shadow: rgba(0, 0, 0, 0.3);
}
```

### Animations (CSS)
- Page transitions: fade-in 200ms
- Progress bar: width transition 300ms ease
- Table rows: hover scale/glow effect
- Cards: subtle lift on hover (translateY -2px)
- Modal/overlay: fade + scale 250ms
- Toast notifications: slide-in from right 300ms, fade-out 500ms
- Loading spinner: rotating ring (CSS only, no images)

### Responsive
- Desktop-first but works down to 1024px width
- Tables become scrollable on smaller screens
- Cards stack vertically on narrow viewports

## Implementation Plan

### Phase 1 — Backend (`server.py`)
1. FastAPI app with CORS
2. Read existing `_registry` at startup
3. Scan existing report directories for status
4. Implement all `GET` endpoints (edges, indicators, report JSON/PNG, ranking, OOS)
5. Implement async `POST /api/analyze` with SSE progress
6. Implement `POST /api/oos-validate` with SSE progress
7. Implement `POST /api/edges/create`

### Phase 2 — Frontend (`index.html` + `app.css` + `app.js`)
1. Dark theme CSS framework
2. Hash-based SPA router
3. API client module (fetch wrappers)
4. Edge list view with search/filter/sort/pagination
5. Edge detail view with charts
6. Ranking view with interactive bar chart
7. OOS validation view
8. Create edge form
9. Progress bar system with SSE connection
10. Toast notification system
