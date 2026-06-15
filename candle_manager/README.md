# Market Data Manager v2.0

Récupération unifiée de données crypto depuis plusieurs exchanges (Binance, Bybit, Deribit) — gratuit, sans authentification.

## Installation

```bash
pip install ccxt pandas loguru requests
```

## Utilisation rapide

```python
from market_data_manager import MarketDataManager, Metric

mgr = MarketDataManager(cache_dir="./cache")

# OHLCV (Binance Spot)
df = mgr.get("ohlcv", "BTC/USDT", "1h", since="2024-01-01", until="2024-06-01")

# Funding Rate (Binance Futures)
df = mgr.get("funding_rate", "DOGE/USDT", "8h", since="2024-01-01")

# Open Interest (Bybit)
df = mgr.get("open_interest", "BTC/USDT", "1h", since="2024-01-01")

# Taker Volume (Binance Futures klines)
df = mgr.get("taker_volume", "ETH/USDT", "4h", since="2024-01-01")

# Liquidations (Deribit — BTC/ETH uniquement)
df = mgr.get("liquidations", "BTC/USDT", "1d", since="2024-01-01")

# Long/Short Ratio (Bybit)
df = mgr.get("long_short_ratio", "BTC/USDT", "1h", since="2024-01-01")
```

## Métriques disponibles

| Métrique | Source | Depuis | Granularités | Colonnes |
|---|---|---|---|---|
| `ohlcv` | Binance Spot | Nov 2019 | 1m→1M | open, high, low, close, volume |
| `funding_rate` | Binance Futures | Nov 2019 | 2h, 4h, 8h | funding_rate, mark_price |
| `open_interest` | Bybit | Mai 2020 | 5m→1d | open_interest, open_interest_usd |
| `taker_volume` | Binance Futures | Nov 2019 | 1m→1M | taker_buy_base, taker_sell_base, taker_buy_quote, taker_sell_quote, taker_buy_ratio, taker_sell_ratio |
| `liquidations` | Deribit | 2018 | 1h, 4h, 1d | long_size, long_size_usd, long_avg_price, short_size, short_size_usd, short_avg_price |
| `long_short_ratio` | Bybit | Juil 2020 | 5m→1d | buy_ratio, sell_ratio, ls_ratio |

## API complète

```python
# Récupérer des données
df = mgr.get(metric, symbol, timeframe, since="YYYY-MM-DD", until="YYYY-MM-DD", limit=N, force_refresh=False)

# Gestion du cache
mgr.refresh_cache(metric, symbol, timeframe)    # Mise à jour incrémentale
mgr.clear_cache(metric?, symbol?, timeframe?)   # Supprimer le cache
mgr.cache_info()                                # État du cache

# Informations
mgr.available_metrics()                         # Liste des métriques
mgr.available_symbols(metric)                   # Symboles disponibles
```

## Fonctionnalités

- Cache automatique (pickle) avec écritures atomiques
- Mise à jour incrémentale du cache (seul le gap manquant est téléchargé)
- Rate limiting par exchange (thread-safe)
- Mapping automatique des symboles (format canonique "BASE/QUOTE")
- Ajustement automatique de l'OI Bybit (bilateral → unilateral, avant juin 2026)
- Resampling des liquidations Deribit (événements bruts → timeframe demandé)
- Gestion d'erreurs complète avec exceptions typées

## Limitations connues

- **Liquidations** : Seuls BTC et ETH sont supportés (Deribit inverse perpetuals). L'API Deribit ne distingue pas long/short, donc `short_size` est toujours 0 et le total est dans `long_size`.
- **Open Interest Bybit** : L'API ne retourne plus `openInterestUsd`, la colonne `open_interest_usd` sera NaN.
- **Funding Rate** : Granularité minimale = 2h (certains contrats 4h ou 8h).
