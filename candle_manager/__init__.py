"""
Module de gestion intelligente des candles de trading.

Fournit un système de téléchargement, mise en cache et rafraîchissement
automatique des données OHLCV depuis Binance via CCXT.
"""

from .candle_manager import CandleManager

__all__ = ['CandleManager']
__version__ = '1.0.0'
