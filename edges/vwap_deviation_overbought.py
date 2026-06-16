"""
VWAP Deviation Overbought
Generated edge from formula engine.
Short: close > vwap(close, volume) * 1.02 & rsi(close, 14) > 65
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def VWAP_Deviation_Overbought_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close > vwap(close, volume) * 1.02 & rsi(close, 14) > 65', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='VWAP Deviation Overbought',
        entry_condition=VWAP_Deviation_Overbought_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price 2% above VWAP with high RSI signals abnormal deviation from volume-weighted mean.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

