"""
Low Std Dev Breakout
Generated edge from formula engine.
Long: rolling_std(close, 20) < rolling_std(close, 20).shift(5) & close > sma(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Low_Std_Dev_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('rolling_std(close, 20) < rolling_std(close, 20).shift(5) & close > sma(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Low Std Dev Breakout',
        entry_condition=Low_Std_Dev_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Declining volatility with price above mean signals coiling for upside expansion.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

