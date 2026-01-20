"""Equilibrium detector.

Ce module calcule le midpoint (équilibre) entre un swing high et un swing
low récents et génère un signal lorsque le prix touche cette zone.  Un
signal « equilibrium » indique simplement que le prix se trouve à
proximité de la moitié de l'impulsion récente; il n'a pas de direction
intrinsèque (il peut être utilisé comme confluence dans un playbook).
"""

from __future__ import annotations

from typing import List, Dict, Any
from models.market_data import Candle
from models.setup import ICTPattern


def detect_equilibrium(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Détecte un équilibre lorsque le prix touche le midpoint d'une impulsion.

    Args:
        candles: Liste de Candle triées par timestamp croissant.
        timeframe: Timeframe de travail.
        config: Paramètres (lookback_swing, tolerance_pct).

    Returns:
        Liste de signaux equilibrium (ICTPattern).
    """
    results: List[ICTPattern] = []
    n = len(candles)
    if n < 3:
        return results
    lookback = int(config.get('lookback_swing', 20))
    tolerance_pct = float(config.get('tolerance_pct', 0.10))
    lb = min(lookback, n)
    window = candles[-lb:]
    # Identifier swing high et low dans la fenêtre
    swing_high = max(c.high for c in window)
    swing_low = min(c.low for c in window)
    midpoint = (swing_high + swing_low) / 2.0
    last_candle = candles[-1]
    price = last_candle.close
    tolerance = midpoint * tolerance_pct
    if abs(price - midpoint) <= tolerance:
        # Équilibre touché
        results.append(ICTPattern(
            symbol=last_candle.symbol,
            timeframe=timeframe,
            pattern_type='equilibrium',
            direction='touch',
            details={
                'eq_price': midpoint,
                'impulse_high': swing_high,
                'impulse_low': swing_low,
                'close_price': price,
                'tolerance': tolerance,
            },
            strength=min(1.0 - (abs(price - midpoint) / tolerance if tolerance > 0 else 0), 1.0),
            confidence=0.6,
        ))
    return results