# 📊 Candle Manager

Module Python pour récupérer et cacher les candles de trading depuis Binance via CCXT.

## 🚀 Installation

```bash
pip install ccxt pandas loguru
```

## 💡 Utilisation

```python
from candle_manager import CandleManager

manager = CandleManager(cache_dir="./cache")

# Dernières N candles
df = manager.get_candles("BTC/USDT", "1h", limit=100)

# Période spécifique (date range)
df = manager.get_candles("ETH/USDT", "4h", since="2025-12-01", until="2025-12-31")
```

## 📋 Timeframes Supportés

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`

## 🔧 Méthodes

```python
# Récupérer des candles
df = manager.get_candles(symbol, timeframe, since=None, until=None, limit=None, force_refresh=False)

# Gestion du cache
manager.get_cache_info()              # Voir le cache
manager.refresh_cache(symbol, tf)     # Rafraîchir
manager.clear_cache()                 # Nettoyer

# Symboles disponibles
manager.get_available_symbols()
```

## 📊 DataFrame Retourné

| Colonne | Type |
|---------|------|
| timestamp (index) | datetime |
| open | float |
| high | float |
| low | float |
| close | float |
| volume | float |

## ✨ Fonctionnalités

- ✅ Cache automatique (pickle)
- ✅ Refresh incrémental
- ✅ Rate limiting Binance
- ✅ Multi-batch automatique (> 1000 candles)
- ✅ Logs via loguru

## 🤖 Pour les IA

Interface simple :
```python
df = manager.get_candles("BTC/USDT", "1h", limit=100)
# → DataFrame Pandas avec OHLCV, index datetime, trié, sans doublons
```

Voir [QUICK_START_AI.py](QUICK_START_AI.py) pour exemples.


