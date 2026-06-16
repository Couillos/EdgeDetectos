"""
Keltner Breakout Down
Generated edge from formula engine.
Short: cross_below(close, keltner_lower(high, low, close, 20, 2))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Keltner_Breakout_Down_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cross_below(close, keltner_lower(high, low, close, 20, 2))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Keltner Breakout Down',
        entry_condition=Keltner_Breakout_Down_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price breaking below Keltner lower channel signals volatility expansion with bearish momentum.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

