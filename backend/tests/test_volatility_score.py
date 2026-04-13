"""utils.volatility — score 1m pour contexte playbook."""
from datetime import datetime, timezone

from models.market_data import Candle
from utils.volatility import volatility_score_from_1m


def _c(i: int, o: float, h: float, l: float, cl: float) -> Candle:
    return Candle(
        symbol="SPY",
        timeframe="1m",
        timestamp=datetime(2025, 11, 5, 14, i, tzinfo=timezone.utc),
        open=o,
        high=h,
        low=l,
        close=cl,
    )


def test_volatility_score_flat_market_low():
    # Corps nul : true range piloté par écarts minimes entre closes consécutifs
    flat = [_c(j, 100.0, 100.0, 100.0, 100.0) for j in range(35)]
    s = volatility_score_from_1m(flat, window=30)
    assert s == 0.0


def test_volatility_score_spiky_market_higher():
    candles = []
    p = 100.0
    for j in range(35):
        p += 0.01
        candles.append(_c(j, p, p + 0.5, p - 0.5, p))
    s = volatility_score_from_1m(candles, window=30)
    assert s >= 0.8
