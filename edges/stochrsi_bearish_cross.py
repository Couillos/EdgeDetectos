"""
StochRSI Bearish Cross
Generated edge from formula engine.
Short: cross_below(stochrsi_k(close, 14), stochrsi_d(close, 14)) & stochrsi_k(close, 14) > 80
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def StochRSI_Bearish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cross_below(stochrsi_k(close, 14), stochrsi_d(close, 14)) & stochrsi_k(close, 14) > 80', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='StochRSI Bearish Cross',
        entry_condition=StochRSI_Bearish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='StochRSI K crossing D from overbought zone signals momentum reversal to downside.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

