"""1m pressure-confirmation helper (Aplus_01 brick).

Detects whether the most recent N 1m bars contain a directional confirmation
in `direction` ∈ {"bullish", "bearish"}. Two confirmation patterns count:

  - **BOS 1m** : current close strictly breaks the highest high (bullish) or
    lowest low (bearish) of the prior `bos_lookback` bars in the window.
  - **Engulfing 1m** : current bar is a full-body engulfing in `direction`
    (current body fully contains the previous body, current closes through
    the previous open in the right direction).

Pure function, no state. Caller passes the recent 1m slice and the desired
direction; returns bool.

Contract:
    has_1m_pressure(bars_1m, direction, window=12, bos_lookback=5) -> bool

Bar shape: any object with `.high`, `.low`, `.open`, `.close` attributes
(Candle pydantic model is fine, namedtuple/dict-with-attrs also work).
"""
from __future__ import annotations

from typing import Any, Sequence


def _is_bullish_engulfing(prev: Any, cur: Any) -> bool:
    prev_o, prev_c = float(prev.open), float(prev.close)
    cur_o, cur_c = float(cur.open), float(cur.close)
    if cur_c <= cur_o:           # current must close up
        return False
    if prev_c >= prev_o:         # previous must be a down-bar
        return False
    return cur_o <= prev_c and cur_c >= prev_o


def _is_bearish_engulfing(prev: Any, cur: Any) -> bool:
    prev_o, prev_c = float(prev.open), float(prev.close)
    cur_o, cur_c = float(cur.open), float(cur.close)
    if cur_c >= cur_o:           # current must close down
        return False
    if prev_c <= prev_o:         # previous must be an up-bar
        return False
    return cur_o >= prev_c and cur_c <= prev_o


def _bos_break(
    window_bars: Sequence[Any], direction: str, bos_lookback: int
) -> bool:
    if len(window_bars) < bos_lookback + 1:
        return False
    cur = window_bars[-1]
    prior = window_bars[-(bos_lookback + 1):-1]
    if direction == "bullish":
        prior_high = max(float(b.high) for b in prior)
        return float(cur.close) > prior_high
    if direction == "bearish":
        prior_low = min(float(b.low) for b in prior)
        return float(cur.close) < prior_low
    return False


def has_1m_pressure(
    bars_1m: Sequence[Any],
    direction: str,
    window: int = 12,
    bos_lookback: int = 5,
) -> bool:
    """True if the last `window` 1m bars contain BOS or engulfing in direction.

    `direction` ∈ {"bullish", "bearish"}. Anything else → False.
    Empty / too-short input → False (no false positives on cold start).
    """
    if direction not in ("bullish", "bearish"):
        return False
    if not bars_1m:
        return False
    win = list(bars_1m)[-window:]
    if len(win) < 2:
        return False

    if _bos_break(win, direction, bos_lookback):
        return True

    for i in range(1, len(win)):
        prev, cur = win[i - 1], win[i]
        if direction == "bullish" and _is_bullish_engulfing(prev, cur):
            return True
        if direction == "bearish" and _is_bearish_engulfing(prev, cur):
            return True

    return False
