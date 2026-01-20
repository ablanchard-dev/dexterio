"""Breaker Block detector.

Ce module détecte les situations où un order block identifié précédemment
est invalidé (le prix traverse la zone) et où la zone peut servir de
support/résistance à l'envers.  Cette implémentation simplifiée
considère qu'un breaker est déclenché dès que le prix traverse la
zone de l'order block.  Elle ne modélise pas explicitement le retest
après la cassure mais fournit un signal de changement de contexte.
"""

from __future__ import annotations

from typing import List, Dict, Any
from models.market_data import Candle
from models.setup import ICTPattern


def detect_breaker_blocks(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Détecte des breaker blocks en examinant le franchissement des zones OB.

    Args:
        candles: Liste de Candle triées par timestamp croissant.
        timeframe: Timeframe de travail.
        config: Paramètres (lookback_ob, tolerance_pct).

    Returns:
        Liste de signaux breaker_block (ICTPattern).
    """
    results: List[ICTPattern] = []
    n = len(candles)
    if n < 5:
        return results
    lookback = int(config.get('lookback_ob', 20))
    tolerance_pct = float(config.get('tolerance_pct', 0.05))
    lb = min(lookback, n - 1)
    window = candles[-lb:]
    last_candle = candles[-1]
    price = last_candle.close
    # Identifier un order block récent via la même logique que detect_order_blocks
    # Boucle pour la dernière cassure haussière ou baissière
    swing_high = max(c.high for c in window)
    swing_low = min(c.low for c in window)
    # Initialiser zone OB à None
    zone = None
    direction = None
    # Cassure haussière
    if last_candle.close > swing_high:
        # Dernière bougie bearish
        for c in reversed(window[:-1]):
            if c.close < c.open:
                if config.get('range_type', 'body').lower() == 'body':
                    zone = (min(c.open, c.close), max(c.open, c.close))
                else:
                    zone = (c.low, c.high)
                direction = 'bullish'
                break
    # Cassure baissière
    elif last_candle.close < swing_low:
        for c in reversed(window[:-1]):
            if c.close > c.open:
                if config.get('range_type', 'body').lower() == 'body':
                    zone = (min(c.open, c.close), max(c.open, c.close))
                else:
                    zone = (c.low, c.high)
                direction = 'bearish'
                break
    if zone is None or direction is None:
        return results
    zone_low, zone_high = zone
    # Vérifier si le prix actuel traverse l'OB (côté opposé)
    # Pour un OB haussier, un breaker survient quand la clôture passe sous la zone low
    if direction == 'bullish' and price < zone_low * (1 - tolerance_pct):
        results.append(ICTPattern(
            symbol=last_candle.symbol,
            timeframe=timeframe,
            pattern_type='breaker_block',
            direction='bearish',
            details={
                'source_ob_direction': 'bullish',
                'zone_low': zone_low,
                'zone_high': zone_high,
                'close_price': price,
                'broken_at': last_candle.timestamp.isoformat(),
            },
            strength=1.0,
            confidence=0.6,
        ))
    # Pour un OB baissier, breaker quand la clôture passe au dessus de la zone high
    if direction == 'bearish' and price > zone_high * (1 + tolerance_pct):
        results.append(ICTPattern(
            symbol=last_candle.symbol,
            timeframe=timeframe,
            pattern_type='breaker_block',
            direction='bullish',
            details={
                'source_ob_direction': 'bearish',
                'zone_low': zone_low,
                'zone_high': zone_high,
                'close_price': price,
                'broken_at': last_candle.timestamp.isoformat(),
            },
            strength=1.0,
            confidence=0.6,
        ))
    return results