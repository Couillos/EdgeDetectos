"""
Vol Contraction Breakout
Generated edge from formula engine.
Long: (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)) < (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)).shift(5) & close > ema(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Vol_Contraction_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('(bb_upper(close, 20, 2) - bb_lower(close, 20, 2)) < (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)).shift(5) & close > ema(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Vol Contraction Breakout',
        entry_condition=Vol_Contraction_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Narrowing BB width with price above EMA signals coiling for upside breakout.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

