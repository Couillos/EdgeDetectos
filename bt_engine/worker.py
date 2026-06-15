"""
Multiprocessing worker for batch edge analysis.

Memory optimisation: on Linux with `fork`, workers inherit the parent's memory.
Use `set_shared_df(df)` in the parent BEFORE spawning workers to avoid each
worker reloading the full dataframe from parquet.
"""
import json, os, sys, re, logging, warnings
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from analysis.report import analyze_edge

# ── Shared DataFrame (inherited via fork, zero-copy) ──────────────────
_SHARED_DF: Optional[pd.DataFrame] = None


def set_shared_df(df: pd.DataFrame):
    """Set the DataFrame to be shared across forked worker processes.
    Call this in the parent process BEFORE spawning worker processes.
    Workers inherit the reference via fork copy-on-write (no memory copy)."""
    global _SHARED_DF
    _SHARED_DF = df


# ── Worker count capped by available memory ───────────────────────────

def _available_memory_mb() -> float:
    """Return available RAM in MB."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:
        pass
    # Fallback: read /proc/meminfo on Linux
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return float(line.split()[1]) / 1024
                if line.startswith('MemFree:'):
                    return float(line.split()[1]) / 1024
    except Exception:
        pass
    return 64 * 1024  # assume 64GB


def _optimal_workers(df: Optional[pd.DataFrame] = None,
                     max_workers: Optional[int] = None) -> int:
    """Return safe worker count based on available memory and dataframe size."""
    cpu_count = os.cpu_count() or 4
    hard_limit = min(max_workers or cpu_count, cpu_count)

    if df is not None and len(df) > 0 and len(df.columns) > 0:
        df_mb = max(df.memory_usage(deep=True).sum() / (1024 * 1024), 0.1)
        avail_mb = _available_memory_mb()
        max_by_mem = max(1, int(avail_mb / (df_mb * 2.5)))
        return min(hard_limit, max_by_mem)
    return hard_limit


# ── Logging for worker processes ──────────────────────────────────────

_log_dir = Path(__file__).parent.parent / 'logs'
_log_dir.mkdir(parents=True, exist_ok=True)
_fh_warn = logging.FileHandler(str(_log_dir / 'warning.log'), encoding='utf-8')
_fh_warn.setLevel(logging.WARNING)
_fh_warn.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s][worker] %(message)s'))
_fh_err = logging.FileHandler(str(_log_dir / 'error.log'), encoding='utf-8')
_fh_err.setLevel(logging.ERROR)
_fh_err.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s][worker] %(message)s'))
logging.getLogger().addHandler(_fh_warn)
logging.getLogger().addHandler(_fh_err)
logging.captureWarnings(True)


def _mp_run_edge(args):
    edge_name, data_path, sm_path, quick, bt_path, reports_dir_name = args
    sys.path.insert(0, os.path.dirname(bt_path))
    import pandas as pd
    import matplotlib; matplotlib.use('Agg')
    from edge_registry import register_edge, get_edge, _registry, Edge, ConditionFn
    # Use shared DataFrame via fork inheritance (zero-copy) when available
    global _SHARED_DF
    if _SHARED_DF is not None:
        df = _SHARED_DF
    else:
        df = pd.read_parquet(data_path)
    def momentum_sma20(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        s = pd.Series(0, index=d.index)
        s[d['close'] > sma20] = 1; s[d['close'] < sma20] = -1
        return s
    register_edge(Edge(name="Price vs SMA20", entry_condition=momentum_sma20, close_horizons=[1,6,24], description=""))
    def rsi_condition(d, period=14):
        delta = d['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean(); avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l; rsi = 100 - (100 / (1 + rs))
        s = pd.Series(0, index=d.index); s[rsi < 30] = 1; s[rsi > 70] = -1; return s
    register_edge(Edge(name="RSI 14 (30/70)", entry_condition=rsi_condition, close_horizons=[1,6,24], description=""))
    def bb_condition(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean(); sd = d['close'].rolling(period).std()
        upper = sma + std * sd; lower = sma - std * sd
        s = pd.Series(0, index=d.index); s[d['close'] < lower] = 1; s[d['close'] > upper] = -1; return s
    register_edge(Edge(name="Bollinger Bands (20,2)", entry_condition=bb_condition, close_horizons=[1,6,24], description=""))
    edges_dir = Path(bt_path).parent / "edges"
    if edges_dir.exists():
        for pyfile in sorted(edges_dir.glob("*.py")):
            if pyfile.name == '__init__.py' or pyfile.name.startswith('_'): continue
            try:
                ns = {'pd': pd, 'np': np, 'register_edge': register_edge, 'Edge': Edge, 'ConditionFn': ConditionFn, '__builtins__': __builtins__}
                with open(pyfile, encoding='utf-8') as f: code = compile(f.read(), pyfile.name, 'exec'); exec(code, ns)
                if 'register' in ns: ns['register']()
            except Exception as exc:
                logging.getLogger().warning(f"Failed to load edge {pyfile.name}: {exc}")
    edge = _registry.get(edge_name)
    if edge is None: return f"[FAIL] {edge_name}: not found"
    safe_name = re.sub(r'[^\w\s-]', '', edge.name).strip().replace(' ', '_').lower()
    reports_dir = Path(reports_dir_name) / safe_name
    json_path = reports_dir / 'analysis.json'
    if json_path.exists(): return f"[skip] {edge.name}"
    df_analysis = df.copy(); signals = edge.entry_condition(df_analysis)
    df_analysis['signal'] = signals; reports_dir.mkdir(parents=True, exist_ok=True)
    output = str(reports_dir / 'report.png')
    with open(sm_path) as f: sm = json.load(f)
    src = sm.get(edge.name, bt_path)
    try:
        analyze_edge(df_analysis, signal_col='signal', signal_name=edge.name, output_path=output, source_file=src, quick=quick)
        return f"[done] {edge.name}"
    except Exception as e:
        logging.getLogger().error(f"Edge '{edge.name}' failed: {e}", exc_info=True)
        return f"[FAIL] {edge.name}"
