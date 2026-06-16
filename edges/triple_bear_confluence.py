"""
Triple Bear Confluence
Generated edge from formula engine.
Short: close < ema(close, 50) & macd_hist(close, 12, 26, 9) < 0 & obv(close, volume) < obv(close, volume).shift(5)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Triple_Bear_Confluence_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close < ema(close, 50) & macd_hist(close, 12, 26, 9) < 0 & obv(close, volume) < obv(close, volume).shift(5)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Triple Bear Confluence',
        entry_condition=Triple_Bear_Confluence_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Trend below 50-EMA with negative MACD histogram and falling OBV provides triple confirmation.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

