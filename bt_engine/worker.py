"""
Multiprocessing worker for batch edge analysis.

Memory optimisation: on Linux with `fork`, workers inherit the parent's memory.
Use `set_shared_df(df)` in the parent BEFORE spawning workers to avoid each
worker reloading the full dataframe from parquet.
"""
import json, os, sys, re, logging, time
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from analysis.report import analyze_edge

# ── Shared DataFrame (inherited via fork, zero-copy) ──────────────────
_SHARED_DF: Optional[pd.DataFrame] = None


def set_shared_df(df: pd.DataFrame):
    global _SHARED_DF
    _SHARED_DF = df


# ── Memory logging ────────────────────────────────────────────────────

_log_dir = Path(__file__).parent.parent / 'logs'
_log_dir.mkdir(parents=True, exist_ok=True)

_memory_logger = logging.getLogger('worker_memory')
_memory_logger.setLevel(logging.INFO)
_memory_logger.handlers.clear()
_mh = logging.FileHandler(str(_log_dir / 'memory.log'), encoding='utf-8')
_mh.setFormatter(logging.Formatter('%(asctime)s [MEM] %(message)s'))
_memory_logger.addHandler(_mh)


def _rss_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _log_mem(edge_name: str, phase: str, extra: str = ''):
    mem = _rss_mb()
    _memory_logger.info(f"{edge_name:40s} | PID={os.getpid():5d} | {phase:10s} | RSS={mem:8.1f}MB {extra}")


# ── Worker count capped by available memory ───────────────────────────

def _available_memory_mb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:
        pass
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return float(line.split()[1]) / 1024
    except Exception:
        pass
    return 64 * 1024


def _optimal_workers(df: Optional[pd.DataFrame] = None,
                     max_workers: Optional[int] = None,
                     quick: bool = False) -> int:
    cpu_count = os.cpu_count() or 4
    hard_limit = min(max_workers or cpu_count, cpu_count)
    # Realistic per-worker: base ~200MB (python, 1178 edges, imports)
    # + chart ~190MB (matplotlib 4350x5700 figure)
    per_worker_mb = 100 if quick else 400
    avail_mb = _available_memory_mb()
    # Leave 30% headroom for system and parent process
    max_by_mem = max(1, int(avail_mb * 0.7 / per_worker_mb))
    result = min(hard_limit, max_by_mem)
    # Never use more than 12 workers regardless — beyond that the memory
    # overhead of 1178 edge definitions per worker dominates
    result = min(result, 12)
    _memory_logger.info(f"{'[SYSTEM]':40s} | {'_optimal':10s} | "
                        f"avail={avail_mb:.0f}MB per_worker={per_worker_mb}MB "
                        f"hard={hard_limit} result={result}")
    return result


# ── Logging for worker processes ──────────────────────────────────────

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
    edge_name, data_path, sm_path, quick, bt_path, reports_dir_name, force = (args if len(args) == 7 else (*args, False))
    sys.path.insert(0, os.path.dirname(bt_path))
    import pandas as pd
    import matplotlib; matplotlib.use('Agg')
    from edge_registry import register_edge, get_edge, _registry, Edge, ConditionFn
    global _SHARED_DF
    if _SHARED_DF is not None:
        df = _SHARED_DF
    else:
        df = pd.read_parquet(data_path)
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
    if json_path.exists() and not force: return f"[skip] {edge.name}"
    if force and json_path.exists():
        json_path.unlink(missing_ok=True)
        png_path = reports_dir / 'report.png'
        if png_path.exists(): png_path.unlink(missing_ok=True)
    try:
        signals = edge.entry_condition(df)
    except Exception as e:
        logging.getLogger().warning(f"Edge '{edge.name}' entry_condition failed: {e}")
        return f"[FAIL] {edge.name}: {e}"
    df_analysis = df.copy()
    df_analysis['signal'] = signals
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = str(reports_dir / 'report.png')
    with open(sm_path) as f: sm = json.load(f)
    src = sm.get(edge.name, bt_path)
    _log_mem(edge.name, 'start')
    mem_before = _rss_mb()
    try:
        analyze_edge(df_analysis, signal_col='signal', signal_name=edge.name, output_path=output, source_file=src, quick=quick)
        mem_after = _rss_mb()
        _log_mem(edge.name, 'end', f'DELTA={mem_after-mem_before:+.1f}MB')
        del df_analysis
        return f"[done] {edge.name}"
    except Exception as e:
        logging.getLogger().error(f"Edge '{edge.name}' failed: {e}", exc_info=True)
        _log_mem(edge.name, 'FAIL', str(e)[:60])
        return f"[FAIL] {edge.name}"
