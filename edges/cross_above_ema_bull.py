"""
Cross Above EMA Bull
Generated edge from formula engine.
Long: cross_above(close, ema(close, 20)) & close > open
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Cross_Above_EMA_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(close, ema(close, 20)) & close > open', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Cross Above EMA Bull',
        entry_condition=Cross_Above_EMA_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price crossing above EMA with bullish candle confirms trend resumption.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

