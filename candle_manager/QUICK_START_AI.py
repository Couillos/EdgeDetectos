"""
Quick Start - Candle Manager pour IA
=====================================
Exemples concis pour récupérer des candles.
"""

from candle_manager import CandleManager

# Initialisation
manager = CandleManager(cache_dir="./cache")


# === CAS 1: Dernières N candles ===
df = manager.get_candles("BTC/USDT", "1h", limit=100)
print(f"Prix BTC: ${df['close'].iloc[-1]:,.2f}")


# === CAS 2: Période spécifique (date range) ===
df = manager.get_candles("ETH/USDT", "4h", since="2025-12-01", until="2025-12-31")
print(f"Décembre 2025: {len(df)} candles")


# === CAS 3: Multi-paires ===
for pair in ["BTC/USDT", "ETH/USDT", "BNB/USDT"]:
    df = manager.get_candles(pair, "1h", limit=24)
    print(f"{pair}: ${df['close'].iloc[-1]:,.2f}")


# === CAS 4: Multi-timeframes ===
for tf in ["1h", "4h", "1d"]:
    df = manager.get_candles("BTC/USDT", tf, limit=50)
    print(f"{tf}: {len(df)} candles")


# === SYNTAXE ===
"""
df = manager.get_candles(symbol, timeframe, limit=N)
df = manager.get_candles(symbol, timeframe, since=START, until=END)

SYMBOLES: "BTC/USDT", "ETH/USDT", etc.
TIMEFRAMES: "1m", "5m", "15m", "1h", "4h", "1d", "1w"

RÉSULTAT (DataFrame):
    - Index: datetime
    - Colonnes: open, high, low, close, volume
    - Trié chronologiquement
    - Sans doublons
"""
