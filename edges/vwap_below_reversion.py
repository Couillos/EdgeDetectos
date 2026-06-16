"""
VWAP Below Reversion
Generated edge from formula engine.
Long: close < vwap(close, volume) & rsi(close, 14) < 30
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def VWAP_Below_Reversion_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close < vwap(close, volume) & rsi(close, 14) < 30', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='VWAP Below Reversion',
        entry_condition=VWAP_Below_Reversion_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price well below VWAP with oversold RSI suggests institutional mean reversion target.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

