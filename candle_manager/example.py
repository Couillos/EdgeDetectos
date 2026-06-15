"""
Exemples basiques du CandleManager.
"""

from candle_manager import CandleManager
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def main():
    manager = CandleManager(cache_dir="./cache")
    
    print("\n" + "="*60)
    print("Exemple 1: Dernières 100 candles")
    print("="*60)
    df = manager.get_candles("BTC/USDT", "1h", limit=100)
    print(f"Récupéré: {len(df)} candles")
    print(f"Prix actuel: ${df['close'].iloc[-1]:,.2f}")
    
    print("\n" + "="*60)
    print("Exemple 2: Période spécifique (date range)")
    print("="*60)
    df = manager.get_candles("ETH/USDT", "4h", since="2025-12-01", until="2025-12-31")
    print(f"Décembre 2025: {len(df)} candles")
    
    print("\n" + "="*60)
    print("Exemple 3: Multi-timeframes")
    print("="*60)
    for tf in ["1h", "4h", "1d"]:
        df = manager.get_candles("BTC/USDT", tf, limit=10)
        print(f"{tf}: {len(df)} candles - Prix: ${df['close'].iloc[-1]:,.2f}")
    
    print("\n" + "="*60)
    print("Exemple 4: Cache info")
    print("="*60)
    cache_info = manager.get_cache_info()
    if not cache_info.empty:
        print(cache_info[['symbol', 'timeframe', 'candles']].to_string())


if __name__ == "__main__":
    main()
