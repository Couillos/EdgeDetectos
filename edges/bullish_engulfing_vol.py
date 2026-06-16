"""
Bullish Engulfing Vol
Generated edge from formula engine.
Long: engulfing_bull(open, close) & volume > volume.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Bullish_Engulfing_Vol_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('engulfing_bull(open, close) & volume > volume.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Bullish Engulfing Vol',
        entry_condition=Bullish_Engulfing_Vol_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Bullish engulfing candle with volume confirmation signals strong reversal pattern.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

