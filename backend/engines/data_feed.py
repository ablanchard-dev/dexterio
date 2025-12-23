"""Module Data Feed - Récupération données marché"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from config.settings import settings
from models.market_data import Candle

logger = logging.getLogger(__name__)

class DataFeedEngine:
    """Moteur de récupération et gestion des données marché"""
    
    def __init__(self, symbols: List[str] = None, source: str = 'yfinance'):
        self.symbols = symbols or settings.SYMBOLS
        self.source = source
        self.candles_cache = {symbol: {tf: [] for tf in settings.TIMEFRAMES} 
                              for symbol in self.symbols}
        logger.info(f"DataFeedEngine initialized with symbols: {self.symbols}, source: {source}")
    
    def fetch_historical_data(self, symbol: str, period: str = '5d', interval: str = '1m') -> List[Candle]:
        """
        Récupère données historiques via yfinance
        
        Args:
            symbol: Ticker (SPY, QQQ)
            period: Période (1d, 5d, 1mo, etc.)
            interval: Intervalle (1m, 5m, 15m, 1h, 1d)
        
        Returns:
            Liste de Candle objects
        """
        try:
            logger.info(f"Fetching {symbol} data: period={period}, interval={interval}")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return []
            
            # Convertir en Candle objects
            candles = []
            for idx, row in df.iterrows():
                candle = Candle(
                    symbol=symbol,
                    timeframe=interval,
                    timestamp=idx.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                )
                candles.append(candle)
            
            logger.info(f"Fetched {len(candles)} candles for {symbol}")
            return candles
        
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return []
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Récupère le dernier prix connu
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
        return None
    
    def get_candles_for_analysis(self, symbol: str, timeframe: str, count: int = 100) -> List[Candle]:
        """
        Récupère les X dernières bougies pour analyse
        """
        # Mapping interval yfinance
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '1h',  # On prendra 4h en aggrégeant des 1h
            '1d': '1d'
        }
        
        interval = interval_map.get(timeframe, '1m')
        
        # Déterminer la période nécessaire
        if timeframe == '1m':
            period = '5d'
        elif timeframe in ['5m', '15m']:
            period = '5d'
        elif timeframe == '1h':
            period = '1mo'
        elif timeframe == '4h':
            period = '1mo'
        else:  # 1d
            period = '1y'
        
        candles = self.fetch_historical_data(symbol, period=period, interval=interval)
        
        # Retourner les N dernières
        return candles[-count:] if len(candles) > count else candles
    
    def aggregate_to_higher_tf(self, candles_1m: List[Candle], target_tf: str) -> List[Candle]:
        """
        Agrège des bougies 1m vers un timeframe supérieur
        
        Args:
            candles_1m: Liste de bougies 1 minute
            target_tf: Timeframe cible ('5m', '15m', '1h', etc.)
        
        Returns:
            Liste de bougies agrégées
        """
        if not candles_1m:
            return []
        
        # Convertir en DataFrame pour resampling
        df = pd.DataFrame([
            {
                'timestamp': c.timestamp,
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume
            }
            for c in candles_1m
        ])
        df.set_index('timestamp', inplace=True)
        
        # Resample selon timeframe
        tf_map = {
            '5m': '5T',
            '15m': '15T',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        
        resample_rule = tf_map.get(target_tf, '5T')
        
        df_resampled = df.resample(resample_rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Reconvertir en Candle objects
        aggregated_candles = []
        symbol = candles_1m[0].symbol
        
        for idx, row in df_resampled.iterrows():
            candle = Candle(
                symbol=symbol,
                timeframe=target_tf,
                timestamp=idx.to_pydatetime(),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            )
            aggregated_candles.append(candle)
        
        return aggregated_candles
    
    def get_multi_timeframe_data(self, symbol: str) -> Dict[str, List[Candle]]:
        """
        Récupère données pour tous les timeframes nécessaires
        
        Returns:
            Dict avec clés = timeframes, valeurs = listes de Candles
        """
        result = {}
        
        # Récupérer 1m (base)
        candles_1m = self.get_candles_for_analysis(symbol, '1m', count=500)
        result['1m'] = candles_1m[-100:]  # Garder les 100 dernières
        
        # Agréger vers autres TFs
        if candles_1m:
            result['5m'] = self.aggregate_to_higher_tf(candles_1m, '5m')[-100:]
            result['15m'] = self.aggregate_to_higher_tf(candles_1m, '15m')[-100:]
            result['1h'] = self.get_candles_for_analysis(symbol, '1h', count=100)
            result['4h'] = self.aggregate_to_higher_tf(result['1h'], '4h')[-50:]
            result['1d'] = self.get_candles_for_analysis(symbol, '1d', count=50)
        
        logger.info(f"Retrieved multi-timeframe data for {symbol}: " + 
                   f"{', '.join([f'{k}:{len(v)}' for k, v in result.items()])}")
        
        return result
