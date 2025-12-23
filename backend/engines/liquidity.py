"""Module Liquidity - Détection des niveaux de liquidité et sweeps"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.market_data import Candle, LiquidityLevel
from utils.indicators import calculate_pivot_points

logger = logging.getLogger(__name__)

class LiquidityEngine:
    """Moteur de détection et surveillance de la liquidité"""
    
    def __init__(self, sweep_threshold_ticks: float = 0.05):
        """
        Args:
            sweep_threshold_ticks: Nombre de ticks au-delà du niveau pour confirmer sweep
        """
        self.liquidity_levels = {}  # {symbol: [LiquidityLevel, ...]}
        self.sweep_threshold = sweep_threshold_ticks
        self.swept_levels = []
        logger.info(f"LiquidityEngine initialized with sweep_threshold={sweep_threshold_ticks}")
    
    def identify_liquidity_levels(self, symbol: str, multi_tf_data: Dict[str, List[Candle]], 
                                  htf_levels: Dict[str, float]) -> List[LiquidityLevel]:
        """
        Identifie tous les niveaux de liquidité pertinents
        
        Args:
            symbol: Ticker
            multi_tf_data: Données multi-timeframes
            htf_levels: Niveaux HTF déjà identifiés (PDH/PDL, etc.)
        
        Returns:
            Liste de LiquidityLevel objects
        """
        levels = []
        
        # 1. Niveaux HTF (PDH/PDL, session highs/lows)
        for level_type, price in htf_levels.items():
            if price:
                level = LiquidityLevel(
                    symbol=symbol,
                    price=price,
                    level_type=level_type,
                    timeframe='HTF',
                    importance=5 if 'pd' in level_type else 4,
                    description=f"{level_type.upper()} level"
                )
                levels.append(level)
        
        # 2. Relative Equal Highs/Lows sur H1
        h1_candles = multi_tf_data.get('1h', [])
        if h1_candles:
            equal_levels = self._find_equal_highs_lows(h1_candles, tolerance=0.05)
            for eq_level in equal_levels:
                level = LiquidityLevel(
                    symbol=symbol,
                    price=eq_level['price'],
                    level_type=eq_level['type'],  # 'equal_highs' or 'equal_lows'
                    timeframe='1h',
                    importance=3,
                    description=f"{eq_level['count']} equal {eq_level['type']}"
                )
                levels.append(level)
        
        # 3. Pivots M15/M5 (intraday)
        m15_candles = multi_tf_data.get('15m', [])
        if m15_candles:
            pivots = calculate_pivot_points([
                {'high': c.high, 'low': c.low, 'timestamp': c.timestamp}
                for c in m15_candles
            ], lookback=3)
            
            # Derniers pivots highs
            for pivot in pivots['pivot_highs'][-5:]:
                level = LiquidityLevel(
                    symbol=symbol,
                    price=pivot['price'],
                    level_type='pivot_high',
                    timeframe='15m',
                    importance=2,
                    description='M15 Pivot High'
                )
                levels.append(level)
            
            # Derniers pivots lows
            for pivot in pivots['pivot_lows'][-5:]:
                level = LiquidityLevel(
                    symbol=symbol,
                    price=pivot['price'],
                    level_type='pivot_low',
                    timeframe='15m',
                    importance=2,
                    description='M15 Pivot Low'
                )
                levels.append(level)
        
        # Stocker
        self.liquidity_levels[symbol] = levels
        logger.info(f"Identified {len(levels)} liquidity levels for {symbol}")
        
        return levels
    
    def _find_equal_highs_lows(self, candles: List[Candle], tolerance: float = 0.05) -> List[Dict[str, Any]]:
        """
        Trouve les zones où plusieurs highs ou lows sont à des niveaux similaires
        
        Args:
            candles: Liste de bougies
            tolerance: Tolérance pour considérer deux niveaux comme égaux ($)
        
        Returns:
            Liste de dicts avec 'price', 'type', 'count'
        """
        equal_levels = []
        
        # Extraire tous les highs et lows
        highs = [c.high for c in candles[-20:]]  # 20 dernières bougies
        lows = [c.low for c in candles[-20:]]
        
        # Trouver equal highs
        checked_highs = set()
        for i, h1 in enumerate(highs):
            if h1 in checked_highs:
                continue
            
            similar_count = 1
            for j, h2 in enumerate(highs):
                if i != j and abs(h1 - h2) <= tolerance:
                    similar_count += 1
            
            if similar_count >= 2:  # Au moins 2 highs similaires
                equal_levels.append({
                    'price': h1,
                    'type': 'equal_highs',
                    'count': similar_count
                })
                checked_highs.add(h1)
        
        # Trouver equal lows
        checked_lows = set()
        for i, l1 in enumerate(lows):
            if l1 in checked_lows:
                continue
            
            similar_count = 1
            for j, l2 in enumerate(lows):
                if i != j and abs(l1 - l2) <= tolerance:
                    similar_count += 1
            
            if similar_count >= 2:
                equal_levels.append({
                    'price': l1,
                    'type': 'equal_lows',
                    'count': similar_count
                })
                checked_lows.add(l1)
        
        return equal_levels
    
    def detect_sweep(self, symbol: str, current_candle: Candle, 
                     previous_candles: List[Candle]) -> List[Dict[str, Any]]:
        """
        Détecte si un sweep de liquidité s'est produit
        
        Critères de sweep:
        1. Wick dépasse le niveau de liquidité de X ticks
        2. Close retourne de l'autre côté du niveau
        3. Formation d'une bougie de rejet (pin bar, engulfing)
        
        Args:
            symbol: Ticker
            current_candle: Bougie actuelle
            previous_candles: Bougies précédentes pour contexte
        
        Returns:
            Liste de sweeps détectés
        """
        sweeps = []
        levels = self.liquidity_levels.get(symbol, [])
        
        if not levels:
            return sweeps
        
        for level in levels:
            if level.swept:
                continue  # Déjà sweepé
            
            # Vérifier sweep vers le haut (liquidity au-dessus)
            if level.level_type in ['high', 'pivot_high', 'equal_highs', 'pdh', 'asia_high', 'london_high']:
                # Wick doit dépasser le niveau
                if current_candle.high >= level.price + self.sweep_threshold:
                    # Close doit retourner en dessous
                    if current_candle.close < level.price:
                        # C'est un sweep !
                        sweep_details = {
                            'level': level,
                            'candle': current_candle,
                            'sweep_type': 'high_sweep',
                            'wick_beyond': current_candle.high - level.price,
                            'rejection_size': current_candle.high - current_candle.close,
                            'is_strong_rejection': (current_candle.high - current_candle.close) >= current_candle.body * 2
                        }
                        
                        # Marquer comme sweepé
                        level.swept = True
                        level.sweep_timestamp = datetime.utcnow()
                        level.sweep_details = sweep_details
                        
                        sweeps.append(sweep_details)
                        self.swept_levels.append(level)
                        
                        logger.info(f"SWEEP DETECTED: {symbol} swept {level.level_type} at {level.price:.2f}, "
                                   f"high={current_candle.high:.2f}, close={current_candle.close:.2f}")
            
            # Vérifier sweep vers le bas (liquidity en-dessous)
            elif level.level_type in ['low', 'pivot_low', 'equal_lows', 'pdl', 'asia_low', 'london_low']:
                # Wick doit dépasser le niveau
                if current_candle.low <= level.price - self.sweep_threshold:
                    # Close doit retourner au-dessus
                    if current_candle.close > level.price:
                        # C'est un sweep !
                        sweep_details = {
                            'level': level,
                            'candle': current_candle,
                            'sweep_type': 'low_sweep',
                            'wick_beyond': level.price - current_candle.low,
                            'rejection_size': current_candle.close - current_candle.low,
                            'is_strong_rejection': (current_candle.close - current_candle.low) >= current_candle.body * 2
                        }
                        
                        # Marquer
                        level.swept = True
                        level.sweep_timestamp = datetime.utcnow()
                        level.sweep_details = sweep_details
                        
                        sweeps.append(sweep_details)
                        self.swept_levels.append(level)
                        
                        logger.info(f"SWEEP DETECTED: {symbol} swept {level.level_type} at {level.price:.2f}, "
                                   f"low={current_candle.low:.2f}, close={current_candle.close:.2f}")
        
        return sweeps
    
    def get_nearest_liquidity(self, symbol: str, current_price: float, 
                             direction: str = 'both') -> Dict[str, Optional[LiquidityLevel]]:
        """
        Trouve les niveaux de liquidité les plus proches
        
        Args:
            symbol: Ticker
            current_price: Prix actuel
            direction: 'above', 'below', ou 'both'
        
        Returns:
            Dict avec 'above' et/ou 'below'
        """
        levels = self.liquidity_levels.get(symbol, [])
        result = {'above': None, 'below': None}
        
        if not levels:
            return result
        
        # Filtrer les niveaux non sweepés
        active_levels = [l for l in levels if not l.swept]
        
        if direction in ['above', 'both']:
            above_levels = [l for l in active_levels if l.price > current_price]
            if above_levels:
                result['above'] = min(above_levels, key=lambda x: x.price)
        
        if direction in ['below', 'both']:
            below_levels = [l for l in active_levels if l.price < current_price]
            if below_levels:
                result['below'] = max(below_levels, key=lambda x: x.price)
        
        return result
    
    def get_liquidity_levels(self, symbol: str, active_only: bool = True) -> List[LiquidityLevel]:
        """
        Récupère les niveaux de liquidité pour un symbole
        
        Args:
            symbol: Ticker
            active_only: Si True, retourne uniquement les niveaux non sweepés
        
        Returns:
            Liste de LiquidityLevel
        """
        levels = self.liquidity_levels.get(symbol, [])
        
        if active_only:
            return [l for l in levels if not l.swept]
        
        return levels
    
    def get_swept_levels(self, symbol: Optional[str] = None) -> List[LiquidityLevel]:
        """
        Récupère les niveaux sweepés
        
        Args:
            symbol: Si fourni, filtre par symbole
        
        Returns:
            Liste de LiquidityLevel sweepés
        """
        if symbol:
            return [l for l in self.swept_levels if l.symbol == symbol]
        return self.swept_levels
