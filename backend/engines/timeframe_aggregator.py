"""
Timeframe Aggregator - Agrégation incrémentale des TF supérieurs
Maintient les buffers 1m et agrège vers 5m/10m/15m/1h uniquement à la clôture
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models.market_data import Candle


class TimeframeAggregator:
    """
    Agrège les bougies 1m vers les TF supérieurs de manière incrémentale.
    Ne reconstruit les bougies HTF que quand elles clôturent.
    """
    
    def __init__(self):
        # Buffers pour bougies en cours de construction
        self.current_5m: Dict[str, Optional[Candle]] = {}
        self.current_10m: Dict[str, Optional[Candle]] = {}
        self.current_15m: Dict[str, Optional[Candle]] = {}
        self.current_1h: Dict[str, Optional[Candle]] = {}
        self.current_4h: Dict[str, Optional[Candle]] = {}
        self.current_1d: Dict[str, Optional[Candle]] = {}
        
        # Historique des bougies complètes (rolling windows)
        self.candles_1m: Dict[str, List[Candle]] = {}
        self.candles_5m: Dict[str, List[Candle]] = {}
        self.candles_10m: Dict[str, List[Candle]] = {}
        self.candles_15m: Dict[str, List[Candle]] = {}
        self.candles_1h: Dict[str, List[Candle]] = {}
        self.candles_4h: Dict[str, List[Candle]] = {}
        self.candles_1d: Dict[str, List[Candle]] = {}
        
        # Tailles des rolling windows
        self.WINDOW_SIZES = {
            "1m": 500,
            "5m": 200,
            "10m": 150,
            "15m": 100,
            "1h": 50,
            "4h": 20,
            "1d": 10
        }
    
    def add_1m_candle(self, candle: Candle) -> Dict[str, bool]:
        """
        Ajoute une bougie 1m et retourne les flags de clôture HTF.
        
        Returns:
            Dict avec is_close_5m, is_close_10m, is_close_15m, is_close_1h, is_close_4h, is_close_1d
        """
        symbol = candle.symbol
        
        # Initialiser les listes si nécessaire
        if symbol not in self.candles_1m:
            self.candles_1m[symbol] = []
            self.candles_5m[symbol] = []
            self.candles_10m[symbol] = []
            self.candles_15m[symbol] = []
            self.candles_1h[symbol] = []
            self.candles_4h[symbol] = []
            self.candles_1d[symbol] = []
        
        # Ajouter la bougie 1m
        self.candles_1m[symbol].append(candle)
        if len(self.candles_1m[symbol]) > self.WINDOW_SIZES["1m"]:
            self.candles_1m[symbol] = self.candles_1m[symbol][-self.WINDOW_SIZES["1m"]:]
        
        # Déterminer si c'est une clôture HTF
        ts = candle.timestamp
        minute = ts.minute
        hour = ts.hour
        
        is_close_5m = (minute % 5 == 4)  # Minute 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59
        is_close_10m = (minute % 10 == 9)
        is_close_15m = (minute % 15 == 14)
        is_close_1h = (minute == 59)
        
        # 4H: Clôture à 11:59, 15:59, 19:59 UTC (7:59, 11:59, 15:59 ET)
        # Le marché trade 9:30-16:00 ET = 13:30-20:00 UTC
        # Les bougies 4h s'alignent sur : 12:00, 16:00, 20:00 UTC
        is_close_4h = (minute == 59 and hour in [11, 15, 19])
        
        # 1D: Clôture à 19:59 UTC (15:59 ET = market close 16:00 ET)
        is_close_1d = (minute == 59 and hour == 19)
        
        # Mettre à jour les bougies HTF
        self._update_htf_candle(symbol, candle, "5m", is_close_5m)
        self._update_htf_candle(symbol, candle, "10m", is_close_10m)
        self._update_htf_candle(symbol, candle, "15m", is_close_15m)
        self._update_htf_candle(symbol, candle, "1h", is_close_1h)
        self._update_htf_candle(symbol, candle, "4h", is_close_4h)
        self._update_htf_candle(symbol, candle, "1d", is_close_1d)
        
        return {
            "is_close_5m": is_close_5m,
            "is_close_10m": is_close_10m,
            "is_close_15m": is_close_15m,
            "is_close_1h": is_close_1h,
            "is_close_4h": is_close_4h,
            "is_close_1d": is_close_1d
        }
    
    def _update_htf_candle(self, symbol: str, candle_1m: Candle, tf: str, is_close: bool):
        """Met à jour une bougie HTF (5m, 10m, 15m, 1h, 4h, 1d)"""
        current_dict = getattr(self, f"current_{tf}")
        candles_list = getattr(self, f"candles_{tf}")[symbol]
        
        if symbol not in current_dict or current_dict[symbol] is None:
            # Commencer une nouvelle bougie HTF
            current_dict[symbol] = Candle(
                symbol=symbol,
                timeframe=tf,
                timestamp=self._floor_timestamp(candle_1m.timestamp, tf),
                open=candle_1m.open,
                high=candle_1m.high,
                low=candle_1m.low,
                close=candle_1m.close,
                volume=candle_1m.volume
            )
        else:
            # Mettre à jour la bougie en cours
            current = current_dict[symbol]
            current.high = max(current.high, candle_1m.high)
            current.low = min(current.low, candle_1m.low)
            current.close = candle_1m.close
            current.volume += candle_1m.volume
        
        if is_close:
            # Finaliser et ajouter à l'historique
            candles_list.append(current_dict[symbol])
            if len(candles_list) > self.WINDOW_SIZES[tf]:
                candles_list[:] = candles_list[-self.WINDOW_SIZES[tf]:]
            # Réinitialiser
            current_dict[symbol] = None
    
    def _floor_timestamp(self, ts: datetime, tf: str) -> datetime:
        """Arrondit un timestamp au début du timeframe"""
        if tf == "5m":
            minute = (ts.minute // 5) * 5
            return ts.replace(minute=minute, second=0, microsecond=0)
        elif tf == "10m":
            minute = (ts.minute // 10) * 10
            return ts.replace(minute=minute, second=0, microsecond=0)
        elif tf == "15m":
            minute = (ts.minute // 15) * 15
            return ts.replace(minute=minute, second=0, microsecond=0)
        elif tf == "1h":
            return ts.replace(minute=0, second=0, microsecond=0)
        elif tf == "4h":
            hour = (ts.hour // 4) * 4
            return ts.replace(hour=hour, minute=0, second=0, microsecond=0)
        elif tf == "1d":
            return ts.replace(hour=0, minute=0, second=0, microsecond=0)
        return ts
    
    def get_candles(self, symbol: str, tf: str) -> List[Candle]:
        """Retourne les bougies complètes pour un symbole/TF donné"""
        return getattr(self, f"candles_{tf}").get(symbol, [])
    
    def get_current_candle(self, symbol: str, tf: str) -> Optional[Candle]:
        """Retourne la bougie HTF en cours de construction (pour visualisation)"""
        current_dict = getattr(self, f"current_{tf}")
        return current_dict.get(symbol)
