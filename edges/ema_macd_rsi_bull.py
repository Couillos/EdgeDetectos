"""
EMA MACD RSI Bull
Generated edge from formula engine.
Long: close > ema(close, 20) & macd(close, 12, 26) > 0 & rsi(close, 14) > 50 & rsi(close, 14) < 70
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def EMA_MACD_RSI_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close > ema(close, 20) & macd(close, 12, 26) > 0 & rsi(close, 14) > 50 & rsi(close, 14) < 70', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='EMA MACD RSI Bull',
        entry_condition=EMA_MACD_RSI_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price above EMA with positive MACD and RSI in bullish zone provides triple confluence.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

