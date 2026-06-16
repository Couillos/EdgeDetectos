"""
Doji Reversal Up
Generated edge from formula engine.
Long: doji(open, close) & rsi(close, 14) < 40
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Doji_Reversal_Up_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('doji(open, close) & rsi(close, 14) < 40', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Doji Reversal Up',
        entry_condition=Doji_Reversal_Up_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Doji in oversold territory signals indecision that often precedes upward reversal.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

