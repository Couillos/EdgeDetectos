"""
Ichimoku Cloud Bear
Generated edge from formula engine.
Short: close < ichimoku_a(high, low) & close < ichimoku_b(high, low)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Ichimoku_Cloud_Bear_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close < ichimoku_a(high, low) & close < ichimoku_b(high, low)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Ichimoku Cloud Bear',
        entry_condition=Ichimoku_Cloud_Bear_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price below both Ichimoku cloud spans signals strong bearish trend territory.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

