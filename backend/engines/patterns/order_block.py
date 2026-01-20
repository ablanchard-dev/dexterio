"""Order Block detector.

Un order block représente la dernière bougie opposée avant un Break of Structure
(BOS) significatif.  Ce module fournit une fonction de détection simple
adaptée à DexterioBOT.  Pour chaque clôture qui casse le swing high/low
défini sur un lookback, on identifie la bougie de la couleur opposée
immédiatement précédant cette cassure et on crée une zone.  La zone peut
être basée sur la totalité du range (haut/bas) ou uniquement sur le
corps (open/close) selon le paramètre `range_type` défini dans le
patterns_config.
"""

from __future__ import annotations

from typing import List, Dict, Any
from models.market_data import Candle
from models.setup import ICTPattern


def detect_order_blocks(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Détecte les Order Blocks en analysant les Breaks of Structure.

    Args:
        candles: Liste de Candle triées par timestamp croissant.
        timeframe: Timeframe de détection.
        config: Paramètres pour la détection (lookback_bos, range_type).

    Returns:
        Liste de signaux d'order block (ICTPattern).
    """
    results: List[ICTPattern] = []
    n = len(candles)
    if n < 5:
        return results
    lookback = int(config.get('lookback_bos', 20))
    range_type = config.get('range_type', 'body').lower()
    # Limiter lookback pour éviter de dépasser l'index
    lb = min(lookback, n - 1)
    # Déterminer swing high et low sur la fenêtre
    window = candles[-lb:]
    swing_high = max(c.high for c in window)
    swing_low = min(c.low for c in window)
    last_candle = candles[-1]
    # Vérifier cassure haussière
    if last_candle.close > swing_high:
        # Rechercher la dernière bougie bearish dans la fenêtre (avant la cassure)
        ob_candle = None
        for c in reversed(window[:-1]):
            if c.close < c.open:  # bearish
                ob_candle = c
                break
        if ob_candle is not None:
            if range_type == 'body':
                zone_low = min(ob_candle.open, ob_candle.close)
                zone_high = max(ob_candle.open, ob_candle.close)
            else:
                zone_low = ob_candle.low
                zone_high = ob_candle.high
            results.append(ICTPattern(
                symbol=last_candle.symbol,
                timeframe=timeframe,
                pattern_type='order_block',
                direction='bullish',
                details={
                    'bos_level': swing_high,
                    'zone_low': zone_low,
                    'zone_high': zone_high,
                    'mitigated': False,
                },
                strength=1.0,
                confidence=0.7,
            ))
    # Vérifier cassure baissière
    if last_candle.close < swing_low:
        ob_candle = None
        for c in reversed(window[:-1]):
            if c.close > c.open:  # bullish
                ob_candle = c
                break
        if ob_candle is not None:
            if range_type == 'body':
                zone_low = min(ob_candle.open, ob_candle.close)
                zone_high = max(ob_candle.open, ob_candle.close)
            else:
                zone_low = ob_candle.low
                zone_high = ob_candle.high
            results.append(ICTPattern(
                symbol=last_candle.symbol,
                timeframe=timeframe,
                pattern_type='order_block',
                direction='bearish',
                details={
                    'bos_level': swing_low,
                    'zone_low': zone_low,
                    'zone_high': zone_high,
                    'mitigated': False,
                },
                strength=1.0,
                confidence=0.7,
            ))
    return results