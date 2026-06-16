"""
Edge Registry
=============
Shared registry for edge definitions.
Separated from backtest.py to avoid __main__ vs backtest module conflicts.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

Signal = int  # 1=LONG, -1=SHORT, 0=NEUTRAL
ConditionFn = Callable[[pd.DataFrame], pd.Series]


_registry: Dict[str, 'Edge'] = {}

SUPPORTED_METRICS = {
    'ohlcv': 'OHLCV (open, high, low, close, volume)',
    'funding_rate': 'Binance Futures funding rate (funding_rate, mark_price)',
    'open_interest': 'Bybit open interest (open_interest, open_interest_usd)',
    'taker_volume': 'Binance taker volume (taker_buy_*, taker_sell_*)',
    'long_short_ratio': 'Bybit long/short ratio (buy_ratio, sell_ratio, ls_ratio)',
}

DEFAULT_HORIZONS = [1, 4, 6, 12, 24, 48, 72, 168]


@dataclass
class Edge:
    name: str
    entry_condition: ConditionFn
    direction: str  # 'long' or 'short'
    close_horizons: List[int] = field(default_factory=lambda: DEFAULT_HORIZONS)
    color: str = '#2196F3'
    description: str = ''
    metric: str = 'ohlcv'
    timeframe: str = '1h'


def register_edge(edge: Edge):
    _registry[edge.name] = edge
    return edge


def get_edge(name: str) -> Optional[Edge]:
    return _registry.get(name)


def list_edges() -> List[str]:
    return list(_registry.keys())
