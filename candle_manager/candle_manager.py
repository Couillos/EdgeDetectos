"""
Gestionnaire de candles avec cache intelligent et rate limiting.
"""

import ccxt
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from loguru import logger
import time
import asyncio
from threading import Lock


class RateLimiter:
    """Gère le rate limiting pour respecter les limites de Binance."""
    
    def __init__(self, max_requests_per_minute: int = 1200, max_weight_per_minute: int = 6000):
        """
        Args:
            max_requests_per_minute: Nombre max de requêtes par minute (Binance: 1200)
            max_weight_per_minute: Poids max par minute (Binance: 6000)
        """
        self.max_requests = max_requests_per_minute
        self.max_weight = max_weight_per_minute
        self.request_times: List[float] = []
        self.weight_times: List[Tuple[float, int]] = []
        self.lock = Lock()
        
    def wait_if_needed(self, weight: int = 1):
        """Attend si nécessaire pour respecter les limites."""
        with self.lock:
            current_time = time.time()
            minute_ago = current_time - 60
            
            # Nettoyer les anciennes entrées
            self.request_times = [t for t in self.request_times if t > minute_ago]
            self.weight_times = [(t, w) for t, w in self.weight_times if t > minute_ago]
            
            # Calculer le poids actuel
            current_weight = sum(w for _, w in self.weight_times)
            
            # Attendre si on dépasse les limites
            if len(self.request_times) >= self.max_requests * 0.9:  # 90% de la limite
                sleep_time = self.request_times[0] - minute_ago + 1
                if sleep_time > 0:
                    logger.warning(f"Rate limit requêtes atteint, attente de {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    return self.wait_if_needed(weight)
            
            if current_weight + weight >= self.max_weight * 0.9:  # 90% de la limite
                sleep_time = self.weight_times[0][0] - minute_ago + 1
                if sleep_time > 0:
                    logger.warning(f"Rate limit poids atteint, attente de {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    return self.wait_if_needed(weight)
            
            # Enregistrer la nouvelle requête
            self.request_times.append(current_time)
            self.weight_times.append((current_time, weight))


class CandleManager:
    """
    Gestionnaire intelligent de candles avec cache et refresh automatique.
    
    Exemple d'utilisation:
        manager = CandleManager(cache_dir="./cache")
        
        # Récupérer des candles
        df = manager.get_candles("BTC/USDT", "1h", limit=1000)
        
        # Avec dates spécifiques
        df = manager.get_candles(
            "ETH/USDT", 
            "4h",
            since="2024-01-01",
            until="2024-12-31"
        )
    """
    
    # Timeframes supportés par Binance
    VALID_TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    def __init__(self, cache_dir: str = "./cache/candles", exchange: str = "binance"):
        """
        Initialise le gestionnaire de candles.
        
        Args:
            cache_dir: Répertoire pour stocker le cache
            exchange: Exchange à utiliser (défaut: binance)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichier pour stocker les timestamps de listing (JSON pour lisibilité)
        self.listing_cache_path = self.cache_dir / "_listing_timestamps.json"
        self.listing_cache = self._load_listing_cache()
        
        # Initialiser l'exchange
        logger.info(f"Initialisation de l'exchange {exchange}")
        # Utiliser le marché spot par défaut
        self.exchange = getattr(ccxt, exchange)({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        # Rate limiter personnalisé pour plus de contrôle
        self.rate_limiter = RateLimiter()
        
        logger.success("CandleManager initialisé avec succès")
    
    def _get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """Retourne le chemin du fichier cache pour un symbole/timeframe."""
        safe_symbol = symbol.replace('/', '_')
        return self.cache_dir / f"{safe_symbol}_{timeframe}.pkl"
    
    def _load_listing_cache(self) -> dict:
        """Charge le cache des timestamps de listing."""
        if not self.listing_cache_path.exists():
            return {}
        
        try:
            import json
            with open(self.listing_cache_path, 'r') as f:
                cache_data = json.load(f)
            # Convertir les strings ISO en datetime
            cache = {k: pd.to_datetime(v) for k, v in cache_data.items()}
            logger.debug(f"Listing cache chargé: {len(cache)} symboles")
            return cache
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du listing cache: {e}")
            return {}
    
    def _save_listing_cache(self):
        """Sauvegarde le cache des timestamps de listing."""
        try:
            import json
            # Convertir les datetime en strings ISO
            cache_data = {k: v.isoformat() for k, v in self.listing_cache.items()}
            with open(self.listing_cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Listing cache sauvegardé: {len(self.listing_cache)} symboles")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du listing cache: {e}")
    
    def _get_listing_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """
        Récupère le timestamp de listing d'un symbole.
        Méthode simple et directe: demande la première candle depuis le début de Binance.
        
        Returns:
            datetime du premier candle disponible ou None si échec
        """
        # Vérifier le cache
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self.listing_cache:
            cached_ts = self.listing_cache[cache_key]
            logger.debug(f"Listing timestamp depuis cache: {symbol} -> {cached_ts}")
            return cached_ts
        
        # Détecter le timestamp de listing
        logger.info(f"Détection du timestamp de listing pour {symbol} {timeframe}")
        
        try:
            # Binance a été lancé en juillet 2017
            # On demande simplement la première candle disponible depuis cette date
            min_date = datetime(2017, 7, 1)
            test_ts = int(min_date.timestamp() * 1000)
            
            df_test = self._fetch_ohlcv_batch(symbol, timeframe, test_ts, limit=1)
            
            if df_test.empty:
                logger.warning(f"Aucune candle trouvée pour {symbol}")
                return None
            
            # La première candle retournée EST le timestamp de listing
            listing_ts = df_test.index[0]
            
            # Sauvegarder dans le cache
            self.listing_cache[cache_key] = listing_ts
            self._save_listing_cache()
            
            logger.success(f"Timestamp de listing détecté: {symbol} -> {listing_ts}")
            return listing_ts
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection du listing timestamp: {e}")
            return None
    
    def _load_from_cache(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Charge les données depuis le cache."""
        cache_path = self._get_cache_path(symbol, timeframe)
        
        if not cache_path.exists():
            logger.debug(f"Pas de cache pour {symbol} {timeframe}")
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                df = pickle.load(f)
            logger.debug(f"Cache chargé: {len(df)} candles pour {symbol} {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cache: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Sauvegarde les données dans le cache."""
        cache_path = self._get_cache_path(symbol, timeframe)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            logger.debug(f"Cache sauvegardé: {len(df)} candles pour {symbol} {timeframe}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convertit un timeframe en secondes."""
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        
        multipliers = {
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'M': 2592000  # Approximation (30 jours)
        }
        
        return value * multipliers.get(unit, 60)
    
    def _fetch_ohlcv_batch(self, symbol: str, timeframe: str, since: int, limit: int = 1000) -> pd.DataFrame:
        """
        Récupère un batch de candles depuis l'exchange.
        
        Args:
            symbol: Paire de trading (ex: "BTC/USDT")
            timeframe: Granularité (ex: "1h")
            since: Timestamp de début en ms
            limit: Nombre de candles à récupérer (max 1000)
        """
        self.rate_limiter.wait_if_needed(weight=1)
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            if not ohlcv:
                return pd.DataFrame()
            
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.debug(f"Récupéré {len(df)} candles depuis {df.index[0]} jusqu'à {df.index[-1]}")
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des candles: {e}")
            raise
    
    def _fetch_all_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Récupère tous les candles entre deux dates.
        
        Args:
            symbol: Paire de trading
            timeframe: Granularité
            since: Date de début (None = il y a 1000 candles)
            until: Date de fin (None = maintenant)
        """
        all_candles = []
        timeframe_seconds = self._timeframe_to_seconds(timeframe)
        
        # Définir les timestamps
        if until is None:
            until = datetime.now()
        until_ts = int(until.timestamp() * 1000)
        
        if since is None:
            # Par défaut, récupérer les 1000 dernières candles
            since = until - timedelta(seconds=timeframe_seconds * 1000)
        
        # Vérifier et ajuster la date de début par rapport au listing
        listing_ts = self._get_listing_timestamp(symbol, timeframe)
        if listing_ts and since < listing_ts:
            logger.info(f"Ajustement de la date de début: {since} -> {listing_ts} (listing)")
            since = listing_ts
        
        since_ts = int(since.timestamp() * 1000)
        
        logger.info(f"Téléchargement des candles {symbol} {timeframe} de {since} à {until}")
        
        current_ts = since_ts
        total_candles = 0
        
        while current_ts < until_ts:
            df_batch = self._fetch_ohlcv_batch(symbol, timeframe, current_ts, limit=1000)
            
            if df_batch.empty:
                logger.warning("Aucune candle récupérée")
                break
            
            all_candles.append(df_batch)
            total_candles += len(df_batch)
            
            # Mettre à jour le timestamp pour la prochaine batch
            last_ts = int(df_batch.index[-1].timestamp() * 1000)
            current_ts = last_ts + (timeframe_seconds * 1000)
            
            # Petite pause pour éviter le rate limiting
            time.sleep(0.1)
            
            logger.debug(f"Progression: {total_candles} candles téléchargées")
        
        if not all_candles:
            logger.warning("Aucune candle récupérée")
            return pd.DataFrame()
        
        # Combiner tous les DataFrames
        df = pd.concat(all_candles)
        df = df[~df.index.duplicated(keep='last')]  # Supprimer les doublons
        df.sort_index(inplace=True)
        
        logger.success(f"Téléchargement terminé: {len(df)} candles au total")
        return df
    
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Récupère les candles avec gestion intelligente du cache.
        
        Args:
            symbol: Paire de trading (ex: "BTC/USDT")
            timeframe: Granularité (ex: "1h", "4h", "1d")
            since: Date de début (format: "YYYY-MM-DD" ou datetime)
            until: Date de fin (format: "YYYY-MM-DD" ou datetime)
            limit: Nombre de candles à retourner (les plus récentes)
            force_refresh: Forcer le téléchargement même si cache existe
        
        Returns:
            DataFrame avec colonnes: open, high, low, close, volume
            Index: timestamp (datetime)
        
        Exemple:
            # Dernières 500 candles
            df = manager.get_candles("BTC/USDT", "1h", limit=500)
            
            # Période spécifique
            df = manager.get_candles("ETH/USDT", "4h", since="2024-01-01", until="2024-12-31")
        """
        # Validation du timeframe
        if timeframe not in self.VALID_TIMEFRAMES:
            raise ValueError(f"Timeframe invalide. Utilisez: {', '.join(self.VALID_TIMEFRAMES)}")
        
        logger.info(f"Requête: {symbol} {timeframe} (since={since}, until={until}, limit={limit})")
        
        # Convertir les dates string en datetime
        since_dt = pd.to_datetime(since) if since else None
        until_dt = pd.to_datetime(until) if until else None
        
        # Charger depuis le cache
        df_cached = None if force_refresh else self._load_from_cache(symbol, timeframe)
        
        if df_cached is not None and not df_cached.empty:
            # Vérifier si on a besoin de données plus anciennes ou plus récentes
            cache_start = df_cached.index.min()
            cache_end = df_cached.index.max()
            
            need_older = since_dt and since_dt < cache_start
            need_newer = until_dt is None or (until_dt and until_dt > cache_end)
            
            # Télécharger les données manquantes
            if need_older:
                logger.info(f"Téléchargement de données plus anciennes (avant {cache_start})")
                df_older = self._fetch_all_ohlcv(symbol, timeframe, since_dt, cache_start)
                if not df_older.empty:
                    df_cached = pd.concat([df_older, df_cached])
            
            if need_newer:
                logger.info(f"Téléchargement de nouvelles données (après {cache_end})")
                newer_since = cache_end + timedelta(seconds=self._timeframe_to_seconds(timeframe))
                df_newer = self._fetch_all_ohlcv(symbol, timeframe, newer_since, until_dt)
                if not df_newer.empty:
                    df_cached = pd.concat([df_cached, df_newer])
            
            # Sauvegarder le cache mis à jour
            if need_older or need_newer:
                df_cached = df_cached[~df_cached.index.duplicated(keep='last')]
                df_cached.sort_index(inplace=True)
                self._save_to_cache(df_cached, symbol, timeframe)
            
            df = df_cached
        else:
            # Pas de cache, télécharger tout
            logger.info("Pas de cache, téléchargement complet")
            df = self._fetch_all_ohlcv(symbol, timeframe, since_dt, until_dt)
            
            if not df.empty:
                self._save_to_cache(df, symbol, timeframe)
        
        # Filtrer selon les dates demandées
        if since_dt:
            df = df[df.index >= since_dt]
        if until_dt:
            df = df[df.index <= until_dt]
        
        # Limiter le nombre de résultats
        if limit:
            df = df.tail(limit)
        
        logger.success(f"Retour de {len(df)} candles")
        return df
    
    def refresh_cache(self, symbol: str, timeframe: str):
        """
        Met à jour le cache avec les dernières candles.
        
        Args:
            symbol: Paire de trading
            timeframe: Granularité
        """
        logger.info(f"Rafraîchissement du cache pour {symbol} {timeframe}")
        self.get_candles(symbol, timeframe, force_refresh=False)
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Vide le cache.
        
        Args:
            symbol: Si spécifié, vide uniquement ce symbole
            timeframe: Si spécifié avec symbol, vide uniquement cette combinaison
        """
        if symbol and timeframe:
            cache_path = self._get_cache_path(symbol, timeframe)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cache supprimé pour {symbol} {timeframe}")
        elif symbol:
            safe_symbol = symbol.replace('/', '_')
            for cache_file in self.cache_dir.glob(f"{safe_symbol}_*.pkl"):
                cache_file.unlink()
            logger.info(f"Cache supprimé pour {symbol} (tous timeframes)")
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("Tout le cache a été supprimé")
    
    def get_available_symbols(self) -> List[str]:
        """Retourne la liste des symboles disponibles sur l'exchange."""
        self.rate_limiter.wait_if_needed(weight=1)
        markets = self.exchange.load_markets()
        return sorted(markets.keys())
    
    def get_cache_info(self) -> pd.DataFrame:
        """Retourne des informations sur le cache."""
        cache_files = list(self.cache_dir.glob("*.pkl"))
        
        info = []
        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    df = pickle.load(f)
                
                name_parts = cache_file.stem.split('_')
                timeframe = name_parts[-1]
                symbol = '_'.join(name_parts[:-1]).replace('_', '/')
                
                info.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'candles': len(df),
                    'start': df.index.min(),
                    'end': df.index.max(),
                    'size_mb': cache_file.stat().st_size / (1024 * 1024)
                })
            except Exception as e:
                logger.warning(f"Impossible de lire {cache_file}: {e}")
        
        return pd.DataFrame(info)
