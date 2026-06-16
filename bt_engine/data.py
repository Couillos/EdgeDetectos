"""
Data loading and edge registration helpers.
"""
import sys, re
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from edge_registry import Edge, register_edge, _registry, ConditionFn, SUPPORTED_METRICS

CACHE_DIR = Path("./cache")

def load_data(since="2020-01-01", until="2026-06-13", symbol="BTC/USDT",
              metric="ohlcv", timeframe="1h", extra_metrics=None):
    from candle_manager import MarketDataManager, Metric
    mdm = MarketDataManager(cache_dir=str(CACHE_DIR / "market_data"))
    metric_str = metric
    print(f"[data] Loading {symbol} {timeframe} ({metric_str}) from {since} to {until}...")
    metric_enum = Metric.from_string(metric_str)
    df = mdm.get(metric_enum, symbol, timeframe, since=since, until=until)
    if df.empty:
        print(f"[data] WARNING: No data returned for {symbol} {metric_str} {timeframe}")
        df = mdm.get(Metric.OHLCV, symbol, timeframe, since=since, until=until)
    if extra_metrics:
        for em in extra_metrics:
            try:
                em_enum = Metric.from_string(em)
                df_extra = mdm.get(em_enum, symbol, timeframe, since=since, until=until)
                if not df_extra.empty:
                    overlap = df.index.intersection(df_extra.index)
                    df = df.loc[overlap].join(df_extra.loc[overlap], how='inner')
                    print(f"[data] Merged {em} ({len(df_extra.columns)} cols, {len(overlap)} rows overlap)")
            except Exception as e:
                print(f"[data] WARNING: Could not load {em}: {e}")
    print(f"[data] Loaded {len(df)} rows ({df.index[0]} to {df.index[-1]}) columns: {list(df.columns)}")
    return df

def register_example_edges():
    def momentum_sma20_long(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        return (d['close'] > sma20).astype(int)
    register_edge(Edge(name="Price vs SMA20", entry_condition=momentum_sma20_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when close > SMA20"))
    def momentum_sma20_short(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        return (-(d['close'] < sma20)).astype(int)
    register_edge(Edge(name="Price vs SMA20 Short", entry_condition=momentum_sma20_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when close < SMA20"))
    def rsi_oversold_long(d, period=14):
        delta = d['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean(); avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l; rsi = 100 - (100 / (1 + rs))
        return (rsi < 30).astype(int)
    register_edge(Edge(name="RSI 14 Oversold", entry_condition=rsi_oversold_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when RSI < 30"))
    def rsi_overbought_short(d, period=14):
        delta = d['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean(); avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l; rsi = 100 - (100 / (1 + rs))
        return (-(rsi > 70)).astype(int)
    register_edge(Edge(name="RSI 14 Overbought Short", entry_condition=rsi_overbought_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when RSI > 70"))
    def bb_long(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean(); sd = d['close'].rolling(period).std()
        lower = sma - std * sd
        return (d['close'] < lower).astype(int)
    register_edge(Edge(name="Bollinger Bands (20,2)", entry_condition=bb_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when close < lower band"))
    def bb_short(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean(); sd = d['close'].rolling(period).std()
        upper = sma + std * sd
        return (-(d['close'] > upper)).astype(int)
    register_edge(Edge(name="Bollinger Bands Short (20,2)", entry_condition=bb_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when close > upper band"))

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
