"""Inverse Fair Value Gap (IFVG) Detector.

Ce module contient une fonction utilitaire pour détecter les inversions
de fair value gaps (FVG) conformément à la définition fournise dans le
contrat DexterioBOT.  Une inversion se produit lorsqu'un FVG haussier
est invalidé par une clôture en dessous de sa zone ou qu'un FVG
baissier est invalidé par une clôture au‑dessus de sa zone.  Les
paramètres minimaux et l'ATR sont fournis via un dictionnaire de
configuration (patterns_config.yml).
"""

from __future__ import annotations

from typing import List, Dict, Any
from models.market_data import Candle
from models.setup import ICTPattern

def detect_ifvg(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Détecte les inversions de FVG.

    Un FVG est considéré inversé lorsque le prix ferme au‑delà de la zone
    définie par le FVG (zone_low/zone_high).  La direction de l'IFVG
    correspond au côté opposé du FVG d'origine : un FVG haussier inversé
    génère un signal ifvg de direction « bearish », et inversement.  Le
    paramètre `min_displacement_pct` indique le déplacement minimum
    nécessaire (en pourcentage du prix) entre la clôture et la zone pour
    valider le signal.

    Args:
        candles: Liste de bougies (Candle) triées par timestamp croissant.
        timeframe: Identifiant de timeframe (ex : "5m", "15m").
        config: Paramètres spécifiques au détecteur (min_displacement_pct, atr_length).

    Returns:
        Liste de ICTPattern pour chaque IFVG détecté.
    """
    results: List[ICTPattern] = []
    n = len(candles)
    if n < 3:
        return results
    # Charger paramètres
    min_disp_pct = float(config.get('min_displacement_pct', 0.05))
    # Itérer sur les deux dernières bougies uniquement (détection temps réel)
    # On cherche des FVG dans l'historique proche puis on vérifie la dernière
    # bougie pour l'invalidation.
    # Collecter les FVG récents
    fvgs = []  # tuples: (idx_end, zone_low, zone_high, direction)
    for i in range(2, n):
        c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
        # Bullish FVG : gap entre high_{t-2} et low_{t}
        if c1.high < c3.low:
            fvgs.append((i, c1.high, c3.low, 'bullish'))
        # Bearish FVG : gap entre low_{t-2} et high_{t}
        if c1.low > c3.high:
            fvgs.append((i, c3.high, c1.low, 'bearish'))
    # Vérifier la dernière clôture pour invalidation
    last_candle = candles[-1]
    last_close = last_candle.close
    last_price = last_close
    for (idx_end, zone_low, zone_high, fvg_dir) in fvgs:
        # Uniquement considérer les FVG récents (index proche de la fin)
        if idx_end < n - 5:
            continue
        if fvg_dir == 'bullish':
            # invalidation si close < zone_low et déplacement significatif
            if last_close < zone_low:
                displacement = (zone_low - last_close) / last_price
                if displacement >= min_disp_pct:
                    # Signal ifvg bearish
                    results.append(ICTPattern(
                        symbol=last_candle.symbol,
                        timeframe=timeframe,
                        pattern_type='ifvg',
                        direction='bearish',
                        details={
                            'fvg_direction': 'bullish',
                            'zone_low': zone_low,
                            'zone_high': zone_high,
                            'close_price': last_close,
                            'displacement_pct': displacement,
                        },
                        strength=min(displacement * 10, 1.0),
                        confidence=min(0.5 + displacement * 10, 1.0)
                    ))
        elif fvg_dir == 'bearish':
            # invalidation si close > zone_high
            if last_close > zone_high:
                displacement = (last_close - zone_high) / last_price
                if displacement >= min_disp_pct:
                    # Signal ifvg bullish
                    results.append(ICTPattern(
                        symbol=last_candle.symbol,
                        timeframe=timeframe,
                        pattern_type='ifvg',
                        direction='bullish',
                        details={
                            'fvg_direction': 'bearish',
                            'zone_low': zone_low,
                            'zone_high': zone_high,
                            'close_price': last_close,
                            'displacement_pct': displacement,
                        },
                        strength=min(displacement * 10, 1.0),
                        confidence=min(0.5 + displacement * 10, 1.0)
                    ))
    return results