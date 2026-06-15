"""
Quick Start — Market Data Manager v2.0
========================================
Exemples concis pour récupérer toutes les métriques.
"""

from market_data_manager import MarketDataManager, Metric

# Initialisation
mgr = MarketDataManager(cache_dir="./cache")


# === OHLCV (Binance Spot) ===
df = mgr.get("ohlcv", "BTC/USDT", "1h", since="2025-01-01", until="2025-01-15")
print(f"OHLCV: {len(df)} candles | Colonnes: {list(df.columns)}")


# === FUNDING RATE (Binance Futures) ===
df = mgr.get("funding_rate", "DOGE/USDT", "8h", since="2025-01-01")
print(f"Funding Rate: {len(df)} points | Dernier: {df['funding_rate'].iloc[-1]:.6f}")


# === OPEN INTEREST (Bybit) ===
df = mgr.get("open_interest", "BTC/USDT", "1h", since="2025-01-01", until="2025-01-03")
print(f"Open Interest: {len(df)} points | Dernier OI: {df['open_interest'].iloc[-1]:,.0f}")


# === TAKER VOLUME (Binance Futures) ===
df = mgr.get("taker_volume", "ETH/USDT", "4h", since="2025-01-01", until="2025-01-03")
print(f"Taker Volume: {len(df)} points | Buy ratio: {df['taker_buy_ratio'].iloc[-1]:.2%}")


# === LIQUIDATIONS (Deribit — BTC/ETH uniquement) ===
df = mgr.get("liquidations", "BTC/USDT", "1d", since="2024-01-01", until="2024-03-01")
print(f"Liquidations: {len(df)} périodes | Colonnes: {list(df.columns)}")


# === LONG/SHORT RATIO (Bybit) ===
df = mgr.get("long_short_ratio", "BTC/USDT", "1h", since="2025-01-01", until="2025-01-03")
print(f"L/S Ratio: {len(df)} points | Dernier ratio: {df['ls_ratio'].iloc[-1]:.4f}")


# === CACHE INFO ===
info = mgr.cache_info()
if not info.empty:
    print(f"\nCache: {len(info)} fichiers")
    print(info[["metric", "symbol", "timeframe", "rows"]].to_string())


# === SYNTAXE GÉNÉRALE ===
"""
mgr.get(
    metric,          # "ohlcv", "funding_rate", "open_interest",
                     # "taker_volume", "liquidations", "long_short_ratio"
    symbol,          # "BTC/USDT", "ETH/USDT", "DOGE/USDT"
    timeframe,       # "5m", "15m", "1h", "4h", "1d"
    since="YYYY-MM-DD",    # optionnel
    until="YYYY-MM-DD",    # optionnel
    limit=N,               # optionnel
    force_refresh=False    # optionnel
)

RÉSULTAT (DataFrame Pandas):
    - Index: DatetimeIndex UTC (trié, sans doublons)
    - Colonnes: dépendent de la métrique (voir README)
"""
