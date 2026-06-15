"""
Data loading and edge registration helpers.
"""
import sys, re
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from edge_registry import Edge, register_edge, _registry, ConditionFn

CACHE_DIR = Path("./cache")

def load_data(since="2020-01-01", until="2026-06-13", symbol="BTC/USDT"):
    from candle_manager import CandleManager
    print(f"[data] Loading {symbol} 1h from {since} to {until}...")
    manager = CandleManager(cache_dir=str(CACHE_DIR))
    df = manager.get_candles(symbol, "1h", since=since, until=until)
    print(f"[data] Loaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")
    return df

def register_example_edges():
    def momentum_sma20(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        s = pd.Series(0, index=d.index)
        s[d['close'] > sma20] = 1
        s[d['close'] < sma20] = -1
        return s
    register_edge(Edge(name="Price vs SMA20", entry_condition=momentum_sma20,
                       close_horizons=[1, 6, 24], description="Long when close > SMA20, Short when close < SMA20"))
    def rsi_condition(d, period=14):
        delta = d['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean(); avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l; rsi = 100 - (100 / (1 + rs))
        s = pd.Series(0, index=d.index)
        s[rsi < 30] = 1; s[rsi > 70] = -1
        return s
    register_edge(Edge(name="RSI 14 (30/70)", entry_condition=rsi_condition,
                       close_horizons=[1, 6, 24], description="Long when RSI < 30, Short when RSI > 70"))
    def bb_condition(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean(); sd = d['close'].rolling(period).std()
        upper = sma + std * sd; lower = sma - std * sd
        s = pd.Series(0, index=d.index)
        s[d['close'] < lower] = 1; s[d['close'] > upper] = -1
        return s
    register_edge(Edge(name="Bollinger Bands (20,2)", entry_condition=bb_condition,
                       close_horizons=[1, 6, 24], description="Long when close < lower band"))

def load_user_edges():
    edges_dir = Path(__file__).resolve().parent.parent / "edges"
    if not edges_dir.exists():
        return
    for pyfile in sorted(edges_dir.glob("*.py")):
        if pyfile.name == '__init__.py' or pyfile.name.startswith('_'):
            continue
        try:
            ns = {'pd': pd, 'np': np, 'register_edge': register_edge,
                  'Edge': Edge, 'ConditionFn': ConditionFn, '__builtins__': __builtins__}
            code = compile(pyfile.read_text(), pyfile.name, 'exec')
            exec(code, ns)
            if 'register' in ns:
                ns['register']()
        except Exception as e:
            print(f"[edges] SKIP {pyfile.name}: {e}")
