"""Helpers pour détection patterns"""
from typing import List, Dict, Any
from models.market_data import Candle

def detect_trend(candles: List[Candle], lookback: int = 10) -> str:
    """
    Détecte la tendance récente
    
    Returns:
        'uptrend', 'downtrend', ou 'range'
    """
    if len(candles) < lookback:
        return 'unknown'
    
    recent = candles[-lookback:]
    
    # Calculer highs et lows
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    
    # Tendance simple : comparer début vs fin
    first_half_avg = sum(c.close for c in recent[:lookback//2]) / (lookback//2)
    second_half_avg = sum(c.close for c in recent[lookback//2:]) / (lookback//2)
    
    pct_change = (second_half_avg - first_half_avg) / first_half_avg
    
    if pct_change > 0.005:  # > 0.5%
        return 'uptrend'
    elif pct_change < -0.005:  # < -0.5%
        return 'downtrend'
    else:
        return 'range'

def is_after_uptrend(candles: List[Candle], lookback: int = 5) -> bool:
    """Vérifie si on est après un uptrend"""
    return detect_trend(candles, lookback) == 'uptrend'

def is_after_downtrend(candles: List[Candle], lookback: int = 5) -> bool:
    """Vérifie si on est après un downtrend"""
    return detect_trend(candles, lookback) == 'downtrend'

def is_at_support_resistance(price: float, levels: List[float], tolerance: float = 0.002) -> bool:
    """
    Vérifie si le prix est proche d'un niveau de support/resistance
    
    Args:
        price: Prix actuel
        levels: Liste de niveaux à vérifier
        tolerance: Tolérance en % (default 0.2%)
    
    Returns:
        True si proche d'un niveau
    """
    for level in levels:
        if abs(price - level) / level <= tolerance:
            return True
    return False
