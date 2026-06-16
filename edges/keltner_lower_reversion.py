"""
Keltner Lower Reversion
Generated edge from formula engine.
Long: close < keltner_lower(high, low, close, 20, 1.5) & rsi(close, 14) < 35
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Keltner_Lower_Reversion_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close < keltner_lower(high, low, close, 20, 1.5) & rsi(close, 14) < 35', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Keltner Lower Reversion',
        entry_condition=Keltner_Lower_Reversion_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price below Keltner lower channel with low RSI indicates oversold conditions primed for reversion.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

