"""
VWAP Deviation Oversold
Generated edge from formula engine.
Long: close < vwap(close, volume) * 0.98 & rsi(close, 14) < 35
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def VWAP_Deviation_Oversold_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close < vwap(close, volume) * 0.98 & rsi(close, 14) < 35', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='VWAP Deviation Oversold',
        entry_condition=VWAP_Deviation_Oversold_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price 2% below VWAP with low RSI signals abnormal deviation from volume-weighted mean.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

