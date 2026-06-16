"""
StochRSI Bullish Cross
Generated edge from formula engine.
Long: cross_above(stochrsi_k(close, 14), stochrsi_d(close, 14)) & stochrsi_k(close, 14) < 20
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def StochRSI_Bullish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(stochrsi_k(close, 14), stochrsi_d(close, 14)) & stochrsi_k(close, 14) < 20', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='StochRSI Bullish Cross',
        entry_condition=StochRSI_Bullish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='StochRSI K crossing D from oversold zone signals momentum reversal to upside.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

