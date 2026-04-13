"""Indicateurs de volatilité courts pour le contexte playbook (1m, sans lookahead)."""
from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.market_data import Candle


def volatility_score_from_1m(candles_1m: List["Candle"], window: int = 30) -> float:
    """
    Score non dimensionnel comparable aux seuils YAML (ex. News_Fade volatility_min: 0.8).

    Formule : moyenne des true range sur les `window` dernières bougies 1m, normalisée par le
    dernier close, × 10_000. Typiquement > 0.8 quand le marché bouge, < 0.8 quand il est plat.

    Pas de lookahead : n'utilise que les bougies déjà closes (liste passée par l'appelant).
    """
    if not candles_1m or len(candles_1m) < 2:
        return 0.0
    n = min(window, len(candles_1m))
    tail = candles_1m[-n:]
    prev_close = tail[0].close
    trs: List[float] = []
    for c in tail:
        tr = max(
            c.high - c.low,
            abs(c.high - prev_close),
            abs(c.low - prev_close),
        )
        trs.append(tr)
        prev_close = c.close
    mean_tr = sum(trs) / len(trs)
    close = tail[-1].close
    if close <= 0:
        return 0.0
    return float((mean_tr / close) * 10_000.0)
