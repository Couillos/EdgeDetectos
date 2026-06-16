"""
Donchian Lower Bounce
Generated edge from formula engine.
Long: close <= donchian_lower(high, low, 20) & stoch(high, low, close, 14) < 20
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Donchian_Lower_Bounce_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close <= donchian_lower(high, low, 20) & stoch(high, low, close, 14) < 20', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Donchian Lower Bounce',
        entry_condition=Donchian_Lower_Bounce_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price at Donchian lower bound with deeply oversold stochastic signals statistical extreme.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

