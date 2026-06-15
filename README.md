# EdgeDetectos — Crypto Edge Backtesting Engine

A quantitative framework for designing, backtesting, and validating trading edge strategies on cryptocurrency data. Define entry conditions using a declarative formula language with 95+ technical indicators, run multiprocessor backtests across 8 horizons (1h–168h), and statistically validate against out-of-sample data.

---

## Project Structure

```
.
├── cli.py                      # CLI entry point (argparse dispatch)
├── backtest.py                 # Backward-compatible entry point, delegates to cli.main()
├── formula_engine.py           # Shim → engine/ package
├── edge_analyzer.py            # Shim → analysis/ package
├── oos_validator.py            # Shim → validation/ package (also contains OOSWorker)
├── edge_registry.py            # Edge dataclass + _registry dict
├── generate_lang_doc.py        # Auto-generates LANG.md from indicators
│
├── engine/                     # Formula language core
│   ├── language.py             # Tokenizer, recursive-descent parser, AST nodes
│   ├── indicators.py           # 95+ indicator implementations (10 categories)
│   └── evaluator.py            # AST walker, eval_formula(), generate_edge_file()
│
├── bt_engine/                  # Backtest execution
│   ├── data.py                 # CandleManager loader, edge registration
│   ├── engine.py               # BacktestEngine: run_edge(), stats, reports
│   └── worker.py               # Multiprocessing worker for batch analysis
│
├── analysis/                   # Statistics & reporting
│   ├── core.py                 # Forward returns, horizon stats, bootstrap CI,
│   │                           # Monte Carlo permutation, rolling/yearly/vol regime
│   ├── report.py               # 16-panel dark-themed chart report generator
│   └── ranking.py              # Bar chart ranker across all edges
│
├── validation/                 # OOS validation
│   ├── core.py                 # OOSValidator orchestrator (multiprocess)
│   └── worker.py               # Single-edge OOS worker
│
├── webapp/                     # FastAPI + Vanilla JS SPA
│   ├── server.py               # FastAPI backend (879 lines, SSE progress)
│   ├── templates/index.html    # SPA frontend
│   └── static/                 # app.js (1163 lines), app.css
│
├── edges/                      # 800+ auto-generated edge .py files
├── reports_*/                  # Per-symbol analysis output (JSON + PNG)
├── cache/                      # OHLCV parquet cache
└── candle_manager/             # Candle download & caching library
```

---

## Architecture

```
┌─────────┐   formula string    ┌──────────────────┐
│  CLI /  │ ──────────────────→ │   engine/         │
│  Web UI │                     │  ┌──────────────┐ │
│         │                     │  │ language.py   │ │  Tokenize → Parse → AST
│         │                     │  │ indicators.py │ │  95+ registered functions
│         │                     │  │ evaluator.py  │ │  eval_formula() walks AST
│         │                     │  └──────┬───────┘ │
└─────────┘                            │
       │                         pd.Series (1/-1/0)
       │                                │
       ▼                                ▼
┌────────────────┐            ┌──────────────────┐
│  bt_engine/    │            │  analysis/        │
│  run_edge()    │───────────→│  horizon stats    │
│  compute       │            │  bootstrap CI     │
│  equity curves │            │  MC permutation   │
│                │            │  rolling stats    │
│                │            │  16-panel report  │
└────────────────┘            └──────────────────┘
                                      │
                                      ▼
                              ┌──────────────────┐
                              │  validation/     │
                              │  OOSValidator    │
                              │  IS vs OOS       │
                              │  decay analysis  │
                              │  STRONG/PASS/    │
                              │  WEAK/FAIL       │
                              └──────────────────┘
```

---

## Setup

### Requirements

- Python 3.10+
- Dependencies: `pandas`, `numpy`, `scipy`, `matplotlib`, `fastapi`, `uvicorn`, `ccxt`

```bash
pip install pandas numpy scipy matplotlib fastapi uvicorn ccxt
```

### Data

OHLCV data is loaded automatically via `CandleManager` (ccxt-based). First load caches the data; subsequent runs use the cache.

```bash
# Cache is created automatically on first analysis:
python backtest.py --symbol BTC/USDT --analyze
```

---

## Usage

### 1. CLI — Python CLI (`python backtest.py`)

```bash
# List all available indicators (95+)
python backtest.py --list-indicators

# List all registered edges
python backtest.py --list-edges

# Create a new edge from formulas
python backtest.py --create-edge "RSI Oversold" \
  --long "rsi(close,14) < 30" \
  --horizons "1,4,6,12,24,48,72,168" \
  --desc "Long when RSI drops below 30"

# Create a long/short edge
python backtest.py --create-edge "RSI Mean Reversion" \
  --long "rsi(close,14) < 30" \
  --short "rsi(close,14) > 70" \
  --horizons "1,4,6,12,24,48,72,168"

# Quick analysis (JSON only, no charts)
python backtest.py --quick --analyze

# Full analysis with 16-panel charts
python backtest.py --analyze

# Single edge analysis
python backtest.py --edge "RSI Oversold" --analyze

# Generate ranking chart across all edges
python backtest.py --ranking

# Out-of-sample validation
python backtest.py --oos-validate --symbol BTC/USDT
python backtest.py --oos-validate --symbol DOGE/USDT
```

### 2. Web UI — FastAPI SPA

```bash
python -m uvicorn webapp.server:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000` for the SPA. API endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/edges` | List all edges |
| GET | `/api/indicators` | List all indicators |
| GET | `/api/edges/{name}` | Single edge details |
| GET | `/api/report/{name}/json` | Analysis JSON |
| GET | `/api/report/{name}/png` | Report chart |
| GET | `/api/ranking` | Ranking data |
| GET | `/api/oos/{symbol}` | OOS results |
| POST | `/api/analyze` | Run analysis (SSE progress) |
| POST | `/api/edges/create` | Create new edge |
| POST | `/api/oos-validate` | Run OOS validation (SSE) |

### 3. Python API

```python
from engine.evaluator import eval_formula
import pandas as pd

df = pd.read_parquet("cache/BTC_USDT_1h.pkl")
signals = eval_formula("rsi(close,14) < 30 & close < bb_lower(close,20,2)", df)
# Returns pd.Series with 1 (LONG) or 0 (NEUTRAL)
```

---

## Formula Language

Edges are defined using a declarative formula string parsed by the engine. The language supports:

### Syntax

```
Operators:    +, -, *, /, <, >, <=, >=, ==, !=, & (AND), | (OR)
Shift:        .shift(N)  e.g., close.shift(6)
Functions:    indicator_name(arg1, arg2, ...)
Parens:       (expr) for grouping
Negation:     -expr
```

### Columns

`open`, `high`, `low`, `close`, `volume` — passed by name (no quotes).

### Indicator Categories (95+ total)

| Category | Count | Examples |
|----------|-------|---------|
| Trend | 20+ | `sma`, `ema`, `wma`, `hma`, `adx`, `macd`, `psar`, `ichimoku_*` |
| Momentum | 15+ | `rsi`, `stoch`, `stochrsi`, `cci`, `williams_r`, `mfi`, `roc`, `trix`, `tsi`, `uo` |
| Volatility | 8+ | `bb_lower`, `bb_mid`, `bb_upper`, `atr`, `keltner_*`, `donchian_*` |
| Volume | 10+ | `vwap`, `obv`, `cmf`, `volume_ratio`, `ad_line`, `eom`, `nvi`, `vpt` |
| Pattern | 12+ | `doji`, `engulfing_bull`, `hammer`, `morning_star`, `three_white_soldiers` |
| Math | 8+ | `abs`, `log`, `sqrt`, `cumsum`, `pct_change` |
| Statistical | 6+ | `correlation`, `covariance`, `beta`, `entropy`, `hurst`, `zscore` |
| Mean Reversion | 2 | `zscore`, `percentile` |
| Structure | 4 | `consecutive_green`, `consecutive_red`, `higher_high`, `lower_low` |

Run `python backtest.py --list-indicators` for the full list, or read `LANG.md`.

### Example Formulas

```python
# Simple trend following
close > ema(close, 50)

# RSI oversold with Bollinger Band confluence
rsi(close,14) < 30 & close < bb_lower(close,20,2)

# MACD momentum shift
macd_hist(close,12,26,9) > 0

# Volume-confirmed breakout
close > high.shift(1) & volume > volume.shift(1)

# Market structure (no indicators)
close > high.shift(1) & low > low.shift(1) & close > close.shift(1)

# Volatility squeeze
bb_upper(close,20,2) - bb_lower(close,20,2) < atr(high,low,close,14) * 2

# Multi-condition combo
adx(high,low,close,14) > 25 & close > ema(close,20) & rsi(close,14) > 50
```

---

## Edge Files

Each edge is a self-contained Python file in `edges/`. They are auto-generated by the CLI and follow a strict template:

```python
"""
Edge Name
Long: formula_long
Short: formula_short
"""
import pandas as pd
import numpy as np
from formula_engine import eval_formula

def edge_name_condition(df: pd.DataFrame) -> pd.Series:
    return eval_formula('formula_string', df)

def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Edge Name',
        entry_condition=edge_name_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='...',
    ))
```

**Never edit edge files manually** — always use `--create-edge`.

---

## Horizons

Edges are evaluated across 8 closing horizons by default:

| Horizon | Label | Period |
|---------|-------|--------|
| 1h | +1h | 1 candle |
| 4h | +4h | 4 candles |
| 6h | +6h | 6 candles |
| 12h | +12h | 12 candles |
| 24h | +24h | 24 candles (1 day) |
| 48h | +48h | 48 candles (2 days) |
| 72h | +72h | 72 candles (3 days) |
| 168h | +168h | 168 candles (1 week) |

---

## Analysis Report

Each edge gets a directory in `reports_{SYMBOL}/` containing:

- **`analysis.json`** — Full statistical breakdown per horizon:
  - Mean return, win rate, Sharpe ratio
  - T-test p-value (H0: mean = 0)
  - KS-test p-value (signal vs random distribution)
  - Monte Carlo permutation p-value
  - Bootstrap 95% CI
  - Rolling & yearly stats
  - Vol regime analysis
- **`report.png`** — 16-panel dark-themed chart report:
  1. Horizon mean returns
  2. Win rate by horizon
  3. Sharpe by horizon
  4. Return distribution (24h)
  5. Q-Q plot (24h)
  6. Signal count by horizon
  7. Rolling mean (24h)
  8. Rolling Sharpe
  9. Yearly returns
  10. Equity curves (all horizons)
  11. (reserved)
  12. Vol regime analysis
  13. T-test p-values
  14. MC/KS test p-values
  15. Signal vs random (1h)
  16. Significance matrix

### Verdict

Edges receive a verdict based on statistical significance:
| Verdict | Criteria |
|---------|----------|
| STRONG | ≥ 21 significant tests across all horizons |
| MODERATE | 12–20 significant tests |
| WEAK | 6–11 significant tests |
| NONE | < 6 significant tests |

---

## Out-of-Sample Validation

Split: **IS** (2020-01-01 → 2025-01-31) / **OOS** (2025-01-31 → now)

```bash
python backtest.py --oos-validate --symbol BTC/USDT
python backtest.py --oos-validate --symbol DOGE/USDT
```

Produces:
- `oos_{SYMBOL}.txt` — Full text report with verdict distribution, top/bottom edges, decay analysis, statistical test summaries
- `oos_{SYMBOL}.csv` — Machine-readable results (edge_name, verdict, is_score, oos_score, composite_decay, sharpe/mean/winrate for IS and OOS)

### Verdicts (OOS)

| Verdict | Threshold | Description |
|---------|-----------|-------------|
| STRONG | score ≥ 70 | Robust IS + OOS performance, minimal decay |
| PASS | score ≥ 45 | Acceptable OOS performance |
| WEAK | score ≥ 25 | Degraded but not invalid |
| FAIL | score < 25 | Fails signal count, sign flip, or high decay |

### Decay Metrics

- **Composite decay**: weighted combination of sharpe decay (30%), distribution shift (25%), mean decay (20%), winrate decay (15%), signal frequency change (10%)
- Edges with composite decay > 0.85 are automatically FAIL

---

## Multiprocessing

All batch operations use `multiprocessing.Pool` across all available CPU cores:

- `--analyze`: data pre-computed to parquet in `/tmp/edge_analysis/`
- `--oos-validate`: OOS data pre-computed to parquet in `/tmp/oos_validation/`
- Each worker independently loads the edge registry and data

---

## Extending: Adding a New Indicator

1. Add the function with the `@indicator` decorator in `engine/indicators.py`:
```python
@indicator('my_indicator', 'Description', 'Category', min_args, max_args)
def _my_indicator(data, col, period=14):
    return data[col].rolling(int(period)).mean()
```

2. Regenerate documentation:
```bash
python generate_lang_doc.py
```

3. Verify:
```bash
python backtest.py --list-indicators
```

---

## Adding a New Edge

```bash
python backtest.py --create-edge "My Strategy" \
  --long "rsi(close,14) < 30 & close > ema(close,200)" \
  --short "rsi(close,14) > 70 & close < ema(close,200)" \
  --horizons "1,4,6,12,24,48,72,168" \
  --desc "My custom strategy description"
```
