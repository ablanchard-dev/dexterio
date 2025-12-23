"""Candlestick Pattern Engine - Tier 1 & 2 Patterns"""
import logging
from typing import List, Optional
from datetime import datetime
from models.market_data import Candle
from models.setup import PatternDetection
from .helpers import detect_trend, is_after_uptrend, is_after_downtrend, is_at_support_resistance

logger = logging.getLogger(__name__)

class CandlestickPatternEngine:
    """Moteur de détection des patterns de chandeliers"""
    
    def __init__(self):
        logger.info("CandlestickPatternEngine initialized")
    
    def detect_patterns(self, candles: List[Candle], timeframe: str, 
                       sr_levels: Optional[List[float]] = None) -> List[PatternDetection]:
        """
        Détecte tous les patterns de chandeliers (Tier 1 & 2)
        
        Args:
            candles: Liste de bougies (minimum 3)
            timeframe: Timeframe des bougies
            sr_levels: Niveaux de support/resistance optionnels
        
        Returns:
            Liste de PatternDetection
        """
        if len(candles) < 3:
            return []
        
        patterns = []
        sr_levels = sr_levels or []
        
        # Single candle patterns (Tier 1)
        patterns.extend(self._detect_single_candle_patterns(candles, timeframe, sr_levels))
        
        # Two candle patterns (Tier 1 & 2)
        patterns.extend(self._detect_two_candle_patterns(candles, timeframe, sr_levels))
        
        # Three candle patterns (Tier 1)
        patterns.extend(self._detect_three_candle_patterns(candles, timeframe, sr_levels))
        
        logger.info(f"Detected {len(patterns)} candlestick patterns on {timeframe}")
        return patterns
    
    def _detect_single_candle_patterns(self, candles: List[Candle], timeframe: str,
                                       sr_levels: List[float]) -> List[PatternDetection]:
        """Détecte patterns 1 bougie"""
        patterns = []
        
        for i in range(-min(5, len(candles)), 0):
            c = candles[i]
            
            # Hammer (Tier 1)
            if self._is_hammer(c) and is_after_downtrend(candles[:i]):
                patterns.append(self._create_pattern(
                    'hammer', 'bullish_reversal', 'strong', [c], 
                    timeframe, sr_levels, 0.9
                ))
            
            # Shooting Star (Tier 1)
            if self._is_shooting_star(c) and is_after_uptrend(candles[:i]):
                patterns.append(self._create_pattern(
                    'shooting_star', 'bearish_reversal', 'strong', [c],
                    timeframe, sr_levels, 0.9
                ))
            
            # Doji (Tier 1)
            doji_result = self._is_doji(c)
            if doji_result:
                patterns.append(self._create_pattern(
                    doji_result['name'], doji_result['type'], 'medium', [c],
                    timeframe, sr_levels, doji_result['score']
                ))
            
            # Marubozu (Tier 2)
            if self._is_bullish_marubozu(c):
                patterns.append(self._create_pattern(
                    'marubozu_bullish', 'continuation', 'medium', [c],
                    timeframe, sr_levels, 0.7
                ))
            
            if self._is_bearish_marubozu(c):
                patterns.append(self._create_pattern(
                    'marubozu_bearish', 'continuation', 'medium', [c],
                    timeframe, sr_levels, 0.7
                ))
            
            # Spinning Top (Tier 1)
            if self._is_spinning_top(c):
                patterns.append(self._create_pattern(
                    'spinning_top', 'indecision', 'weak', [c],
                    timeframe, sr_levels, 0.5
                ))
        
        return patterns
    
    def _detect_two_candle_patterns(self, candles: List[Candle], timeframe: str,
                                    sr_levels: List[float]) -> List[PatternDetection]:
        """Détecte patterns 2 bougies"""
        patterns = []
        
        for i in range(-min(5, len(candles)-1), 0):
            c1, c2 = candles[i-1], candles[i]
            
            # Bullish Engulfing (Tier 1)
            if self._is_bullish_engulfing(c1, c2):
                patterns.append(self._create_pattern(
                    'bullish_engulfing', 'bullish_reversal', 'strong', [c1, c2],
                    timeframe, sr_levels, 1.0
                ))
            
            # Bearish Engulfing (Tier 1)
            if self._is_bearish_engulfing(c1, c2):
                patterns.append(self._create_pattern(
                    'bearish_engulfing', 'bearish_reversal', 'strong', [c1, c2],
                    timeframe, sr_levels, 1.0
                ))
            
            # Piercing Line (Tier 1)
            if self._is_piercing_line(c1, c2):
                patterns.append(self._create_pattern(
                    'piercing_line', 'bullish_reversal', 'strong', [c1, c2],
                    timeframe, sr_levels, 0.85
                ))
            
            # Dark Cloud Cover (Tier 1)
            if self._is_dark_cloud_cover(c1, c2):
                patterns.append(self._create_pattern(
                    'dark_cloud_cover', 'bearish_reversal', 'strong', [c1, c2],
                    timeframe, sr_levels, 0.85
                ))
            
            # Bullish Harami (Tier 2)
            if self._is_bullish_harami(c1, c2):
                patterns.append(self._create_pattern(
                    'bullish_harami', 'bullish_reversal', 'medium', [c1, c2],
                    timeframe, sr_levels, 0.7
                ))
            
            # Bearish Harami (Tier 2)
            if self._is_bearish_harami(c1, c2):
                patterns.append(self._create_pattern(
                    'bearish_harami', 'bearish_reversal', 'medium', [c1, c2],
                    timeframe, sr_levels, 0.7
                ))
        
        return patterns
    
    def _detect_three_candle_patterns(self, candles: List[Candle], timeframe: str,
                                      sr_levels: List[float]) -> List[PatternDetection]:
        """Détecte patterns 3 bougies"""
        patterns = []
        
        for i in range(-min(5, len(candles)-2), 0):
            c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
            
            # Morning Star (Tier 1)
            if self._is_morning_star(c1, c2, c3):
                patterns.append(self._create_pattern(
                    'morning_star', 'bullish_reversal', 'strong', [c1, c2, c3],
                    timeframe, sr_levels, 1.0
                ))
            
            # Evening Star (Tier 1)
            if self._is_evening_star(c1, c2, c3):
                patterns.append(self._create_pattern(
                    'evening_star', 'bearish_reversal', 'strong', [c1, c2, c3],
                    timeframe, sr_levels, 1.0
                ))
            
            # Three White Soldiers (Tier 1)
            if self._is_three_white_soldiers(c1, c2, c3):
                patterns.append(self._create_pattern(
                    'three_white_soldiers', 'continuation', 'strong', [c1, c2, c3],
                    timeframe, sr_levels, 1.0
                ))
            
            # Three Black Crows (Tier 1)
            if self._is_three_black_crows(c1, c2, c3):
                patterns.append(self._create_pattern(
                    'three_black_crows', 'continuation', 'strong', [c1, c2, c3],
                    timeframe, sr_levels, 1.0
                ))
        
        return patterns
    
    # ==================== PATTERN VALIDATORS ====================
    
    def _is_hammer(self, c: Candle) -> bool:
        """Hammer: body ≤ 33% range, lower_wick ≥ 2×body, upper_wick ≤ 0.1×body"""
        return (c.body <= 0.33 * c.total_range and
                c.lower_wick >= 2 * c.body and
                c.upper_wick <= 0.1 * c.body)
    
    def _is_shooting_star(self, c: Candle) -> bool:
        """Shooting Star: body ≤ 33% range, upper_wick ≥ 2×body, lower_wick ≤ 0.1×body"""
        return (c.body <= 0.33 * c.total_range and
                c.upper_wick >= 2 * c.body and
                c.lower_wick <= 0.1 * c.body)
    
    def _is_doji(self, c: Candle) -> Optional[dict]:
        """Doji: open ≈ close"""
        if abs(c.open - c.close) <= 0.001 * c.total_range:
            # Classifier type
            if c.lower_wick >= 2 * c.upper_wick:
                return {'name': 'dragonfly_doji', 'type': 'bullish_reversal', 'score': 0.7}
            elif c.upper_wick >= 2 * c.lower_wick:
                return {'name': 'gravestone_doji', 'type': 'bearish_reversal', 'score': 0.7}
            else:
                return {'name': 'standard_doji', 'type': 'indecision', 'score': 0.5}
        return None
    
    def _is_bullish_marubozu(self, c: Candle) -> bool:
        """Marubozu bullish: upper_wick ≤ 0.05×body, lower_wick ≤ 0.05×body, bullish"""
        return (c.is_bullish and
                c.upper_wick <= 0.05 * c.body and
                c.lower_wick <= 0.05 * c.body)
    
    def _is_bearish_marubozu(self, c: Candle) -> bool:
        """Marubozu bearish"""
        return (c.is_bearish and
                c.upper_wick <= 0.05 * c.body and
                c.lower_wick <= 0.05 * c.body)
    
    def _is_spinning_top(self, c: Candle) -> bool:
        """Spinning Top: body ≤ 33% range, upper_wick ≈ lower_wick"""
        if c.body > 0.33 * c.total_range:
            return False
        ratio = c.upper_wick / c.lower_wick if c.lower_wick > 0 else 999
        return 0.7 <= ratio <= 1.3
    
    def _is_bullish_engulfing(self, c1: Candle, c2: Candle) -> bool:
        """Bullish Engulfing"""
        return (c1.is_bearish and c2.is_bullish and
                c2.open <= c1.close and c2.close >= c1.open and
                c2.body > c1.body)
    
    def _is_bearish_engulfing(self, c1: Candle, c2: Candle) -> bool:
        """Bearish Engulfing"""
        return (c1.is_bullish and c2.is_bearish and
                c2.open >= c1.close and c2.close <= c1.open and
                c2.body > c1.body)
    
    def _is_piercing_line(self, c1: Candle, c2: Candle) -> bool:
        """Piercing Line"""
        return (c1.is_bearish and c2.is_bullish and
                c2.open < c1.low and
                c2.close > (c1.open + c1.close) / 2)
    
    def _is_dark_cloud_cover(self, c1: Candle, c2: Candle) -> bool:
        """Dark Cloud Cover"""
        return (c1.is_bullish and c2.is_bearish and
                c2.open > c1.high and
                c2.close < (c1.open + c1.close) / 2)
    
    def _is_bullish_harami(self, c1: Candle, c2: Candle) -> bool:
        """Bullish Harami"""
        return (c1.is_bearish and c2.is_bullish and
                c2.open > c1.close and c2.close < c1.open)
    
    def _is_bearish_harami(self, c1: Candle, c2: Candle) -> bool:
        """Bearish Harami"""
        return (c1.is_bullish and c2.is_bearish and
                c2.open < c1.close and c2.close > c1.open)
    
    def _is_morning_star(self, c1: Candle, c2: Candle, c3: Candle) -> bool:
        """Morning Star"""
        return (c1.is_bearish and
                c2.body <= 0.3 * c1.body and
                c3.is_bullish and
                c3.close > (c1.open + c1.close) / 2)
    
    def _is_evening_star(self, c1: Candle, c2: Candle, c3: Candle) -> bool:
        """Evening Star"""
        return (c1.is_bullish and
                c2.body <= 0.3 * c1.body and
                c3.is_bearish and
                c3.close < (c1.open + c1.close) / 2)
    
    def _is_three_white_soldiers(self, c1: Candle, c2: Candle, c3: Candle) -> bool:
        """Three White Soldiers"""
        return (all([c.is_bullish for c in [c1, c2, c3]]) and
                c2.open > c1.open and c2.open < c1.close and
                c3.open > c2.open and c3.open < c2.close and
                c2.close > c1.close and c3.close > c2.close)
    
    def _is_three_black_crows(self, c1: Candle, c2: Candle, c3: Candle) -> bool:
        """Three Black Crows"""
        return (all([c.is_bearish for c in [c1, c2, c3]]) and
                c2.open < c1.open and c2.open > c1.close and
                c3.open < c2.open and c3.open > c2.close and
                c2.close < c1.close and c3.close < c2.close)
    
    def _create_pattern(self, name: str, p_type: str, strength: str, 
                       candles: List[Candle], timeframe: str, 
                       sr_levels: List[float], base_score: float) -> PatternDetection:
        """Crée un PatternDetection avec contexte"""
        
        # Vérifier contexte
        at_sr = is_at_support_resistance(candles[-1].close, sr_levels) if sr_levels else False
        
        # Ajuster score selon contexte
        final_score = base_score
        if at_sr:
            final_score *= 1.2
        final_score = min(final_score, 1.0)
        
        return PatternDetection(
            symbol=candles[0].symbol,
            timeframe=timeframe,
            pattern_name=name,
            pattern_type=p_type,
            strength=strength,
            candles_data=[c.model_dump() for c in candles],
            trend_before=detect_trend(candles[:-len(candles)]),
            at_support_resistance=at_sr,
            pattern_score=final_score
        )
