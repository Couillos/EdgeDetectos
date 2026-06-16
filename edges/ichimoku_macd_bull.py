"""
Ichimoku MACD Bull
Generated edge from formula engine.
Long: close > ichimoku_a(high, low) & macd_hist(close, 12, 26, 9) > 0
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Ichimoku_MACD_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close > ichimoku_a(high, low) & macd_hist(close, 12, 26, 9) > 0', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Ichimoku MACD Bull',
        entry_condition=Ichimoku_MACD_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price above Ichimoku cloud with positive MACD histogram provides dual trend-momentum confirmation.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

