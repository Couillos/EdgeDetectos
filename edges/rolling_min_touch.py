"""
Rolling Min Touch
Generated edge from formula engine.
Long: close <= rolling_min(close, 20) * 1.01 & rsi(close, 14) < 30
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Rolling_Min_Touch_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close <= rolling_min(close, 20) * 1.01 & rsi(close, 14) < 30', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Rolling Min Touch',
        entry_condition=Rolling_Min_Touch_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price near 20-bar rolling minimum with oversold RSI signals statistical floor test.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

