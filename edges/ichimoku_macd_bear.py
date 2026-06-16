"""
Ichimoku MACD Bear
Generated edge from formula engine.
Short: close < ichimoku_a(high, low) & macd_hist(close, 12, 26, 9) < 0
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Ichimoku_MACD_Bear_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close < ichimoku_a(high, low) & macd_hist(close, 12, 26, 9) < 0', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Ichimoku MACD Bear',
        entry_condition=Ichimoku_MACD_Bear_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price below Ichimoku cloud with negative MACD histogram provides dual trend-momentum confirmation.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

