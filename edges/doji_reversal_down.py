"""
Doji Reversal Down
Generated edge from formula engine.
Short: doji(open, close) & rsi(close, 14) > 60
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Doji_Reversal_Down_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('doji(open, close) & rsi(close, 14) > 60', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Doji Reversal Down',
        entry_condition=Doji_Reversal_Down_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Doji in overbought territory signals indecision that often precedes downward reversal.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

