"""
Multiprocessing worker for batch edge analysis.
"""
import json, os, sys, re, logging, warnings
from pathlib import Path
import pandas as pd
import numpy as np
from analysis.report import analyze_edge

# Worker processes need their own file logging setup
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
