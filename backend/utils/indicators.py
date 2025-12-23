"""Indicateurs techniques et détection de structure"""
from typing import List, Dict, Any, Optional
import numpy as np

def calculate_pivot_points(candles: List[Dict[str, Any]], lookback: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calcule les pivot highs et pivot lows
    
    Args:
        candles: Liste de bougies
        lookback: Nombre de bougies de chaque côté pour confirmation
    
    Returns:
        Dict avec 'pivot_highs' et 'pivot_lows'
    """
    pivot_highs = []
    pivot_lows = []
    
    for i in range(lookback, len(candles) - lookback):
        # Pivot High: high[i] > high[i-lookback:i] et high[i] > high[i+1:i+lookback+1]
        is_pivot_high = True
        current_high = candles[i]['high']
        
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j]['high'] >= current_high:
                is_pivot_high = False
                break
        
        if is_pivot_high:
            pivot_highs.append({
                'index': i,
                'price': current_high,
                'timestamp': candles[i]['timestamp']
            })
        
        # Pivot Low
        is_pivot_low = True
        current_low = candles[i]['low']
        
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j]['low'] <= current_low:
                is_pivot_low = False
                break
        
        if is_pivot_low:
            pivot_lows.append({
                'index': i,
                'price': current_low,
                'timestamp': candles[i]['timestamp']
            })
    
    return {'pivot_highs': pivot_highs, 'pivot_lows': pivot_lows}

def detect_structure(candles: List[Dict[str, Any]]) -> str:
    """
    Détermine la structure du marché (uptrend, downtrend, range)
    
    Returns:
        'uptrend', 'downtrend', ou 'range'
    """
    if len(candles) < 20:
        return 'unknown'
    
    # Calculer pivots
    pivots = calculate_pivot_points(candles, lookback=3)
    highs = pivots['pivot_highs']
    lows = pivots['pivot_lows']
    
    if len(highs) < 2 or len(lows) < 2:
        return 'range'
    
    # Vérifier Higher Highs + Higher Lows (uptrend)
    recent_highs = highs[-3:]
    recent_lows = lows[-3:]
    
    higher_highs = all(recent_highs[i]['price'] > recent_highs[i-1]['price'] 
                       for i in range(1, len(recent_highs)))
    higher_lows = all(recent_lows[i]['price'] > recent_lows[i-1]['price'] 
                      for i in range(1, len(recent_lows)))
    
    if higher_highs and higher_lows:
        return 'uptrend'
    
    # Vérifier Lower Highs + Lower Lows (downtrend)
    lower_highs = all(recent_highs[i]['price'] < recent_highs[i-1]['price'] 
                      for i in range(1, len(recent_highs)))
    lower_lows = all(recent_lows[i]['price'] < recent_lows[i-1]['price'] 
                     for i in range(1, len(recent_lows)))
    
    if lower_highs and lower_lows:
        return 'downtrend'
    
    return 'range'

def calculate_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    """
    Calcule Average True Range
    """
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # ATR = moyenne des TR
    return np.mean(true_ranges[-period:])
