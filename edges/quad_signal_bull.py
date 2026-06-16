"""
Quad Signal Bull
Generated edge from formula engine.
Long: close > sma(close, 50) & rsi(close, 14) > 50 & obv(close, volume) > obv(close, volume).shift(5) & adx(high, low, close, 14) > 20
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Quad_Signal_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close > sma(close, 50) & rsi(close, 14) > 50 & obv(close, volume) > obv(close, volume).shift(5) & adx(high, low, close, 14) > 20', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Quad Signal Bull',
        entry_condition=Quad_Signal_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Four-signal confluence combining trend, momentum, volume, and trend strength.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

