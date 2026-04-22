"""ATR-adaptive zigzag directional change — Option A v2 O2.1.

Implements the multi-scale structural pivot detector from QUANT_SYNTHESIS
(video `EuFakzlBLOA`): a zigzag where the reversal threshold `sigma` scales
with local ATR, so the same algorithm yields micro (k1), meso (k3) and macro
(k9) pivots in a single pass.

Contract:
    detect_directional_change(bars, kappa, atr_period=14) -> list[Pivot]
    detect_structure_multi_scale(bars, kappas=(1.0, 3.0, 9.0))
        -> {"k1": [...], "k3": [...], "k9": [...]}

`detect_structure_multi_scale` is LRU-cached on
`(symbol, len(bars), last_bar_timestamp, kappas)` so repeated evaluations on
the same bar return the same pivot list without recompute.

No hidden dependency on any playbook or setup — callable from tp_resolver,
from setup_engine_v2 gates, or from the audit UI.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Sequence, Tuple

from engines.features.pivot import Pivot, PivotType

_DEFAULT_KAPPAS: Tuple[float, float, float] = (1.0, 3.0, 9.0)
_MIN_BARS_FOR_PIVOTS = 3  # need at least some history for an ATR and a swing


def _compute_atr(bars: Sequence[Any], period: int) -> List[float]:
    """Rolling ATR (simple moving average of True Range).

    Returns a list aligned with `bars` where index i holds the ATR computed
    *up to and including* bar i (None → 0.0 padding for the first period-1
    bars so the zigzag has a usable threshold from the start).
    """
    n = len(bars)
    if n == 0:
        return []
    trs: List[float] = []
    prev_close: float | None = None
    for bar in bars:
        high = float(bar.high)
        low = float(bar.low)
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = float(bar.close)

    atr: List[float] = []
    window_sum = 0.0
    for i, tr in enumerate(trs):
        window_sum += tr
        if i >= period:
            window_sum -= trs[i - period]
        if i + 1 >= period:
            atr.append(window_sum / period)
        else:
            # Bootstrapping: use running mean until we have `period` bars.
            atr.append(window_sum / (i + 1))
    return atr


def detect_directional_change(
    bars: Sequence[Any],
    kappa: float,
    atr_period: int = 14,
) -> List[Pivot]:
    """Zigzag with ATR-adaptive threshold `sigma = kappa * ATR(i)`.

    State machine:
        - start in "seeking" mode, tracking running extremes from bar 0.
        - when `high - running_low >= sigma` we confirm the running_low as a
          `low` pivot and flip to tracking highs (mode="up").
        - symmetrically for `running_high - low >= sigma`.
        - pivots alternate high/low by construction.

    This is the standard intuition from `EuFakzlBLOA` — same algorithm used
    by Hurst / fractal-dimension literature. The lag is variable (a pivot is
    confirmed only once price has moved `sigma` away from it).
    """
    n = len(bars)
    if n < _MIN_BARS_FOR_PIVOTS or kappa <= 0:
        return []

    atr = _compute_atr(bars, atr_period)

    pivots: List[Pivot] = []

    # Track running extremes since the last confirmed pivot (or bar 0).
    running_high = float(bars[0].high)
    running_high_idx = 0
    running_low = float(bars[0].low)
    running_low_idx = 0

    # mode: None until the first pivot confirmed; then "up" (seeking next
    # high after a low) or "down" (seeking next low after a high).
    mode: str | None = None

    for i in range(1, n):
        bar = bars[i]
        high = float(bar.high)
        low = float(bar.low)
        sigma = kappa * atr[i] if atr[i] > 0 else 0.0
        if sigma <= 0:
            # No ATR yet → fall back to using the initial range as a floor so
            # we still make progress on flat synthetic fixtures.
            sigma = kappa * max(1e-9, abs(running_high - running_low))

        if high > running_high:
            running_high = high
            running_high_idx = i
        if low < running_low:
            running_low = low
            running_low_idx = i

        if mode is None:
            # First pivot: whichever threshold breaks first decides direction.
            if running_high - low >= sigma and running_high_idx < i:
                pivots.append(
                    Pivot(
                        index=running_high_idx,
                        price=running_high,
                        type="high",
                        timestamp=bars[running_high_idx].timestamp,
                    )
                )
                mode = "down"
                # Reset the running low to track the reversal.
                running_low = low
                running_low_idx = i
            elif high - running_low >= sigma and running_low_idx < i:
                pivots.append(
                    Pivot(
                        index=running_low_idx,
                        price=running_low,
                        type="low",
                        timestamp=bars[running_low_idx].timestamp,
                    )
                )
                mode = "up"
                running_high = high
                running_high_idx = i
            continue

        if mode == "up":
            # Looking to confirm a new high: `running_high` is candidate; we
            # confirm once price retraces by sigma from that peak.
            if running_high - low >= sigma and running_high_idx < i:
                pivots.append(
                    Pivot(
                        index=running_high_idx,
                        price=running_high,
                        type="high",
                        timestamp=bars[running_high_idx].timestamp,
                    )
                )
                mode = "down"
                running_low = low
                running_low_idx = i
        else:  # mode == "down"
            if high - running_low >= sigma and running_low_idx < i:
                pivots.append(
                    Pivot(
                        index=running_low_idx,
                        price=running_low,
                        type="low",
                        timestamp=bars[running_low_idx].timestamp,
                    )
                )
                mode = "up"
                running_high = high
                running_high_idx = i

    return pivots


# ---------------------------------------------------------------------------
# Cached multi-scale entry point
# ---------------------------------------------------------------------------


@lru_cache(maxsize=256)
def _cached_multi_scale(
    cache_key: Tuple[Any, ...],
    bars_tuple: Tuple[Tuple[float, float, float, float, Any], ...],
    kappas: Tuple[float, ...],
    atr_period: int,
) -> Dict[str, List[Pivot]]:
    """LRU-cached worker. `bars_tuple` is a minimal OHLC+timestamp tuple so
    unhashable `Candle` objects don't defeat the cache."""

    class _Bar:
        __slots__ = ("open", "high", "low", "close", "timestamp")

        def __init__(self, o, h, l, c, ts):
            self.open = o
            self.high = h
            self.low = l
            self.close = c
            self.timestamp = ts

    bars = [_Bar(*t) for t in bars_tuple]
    result: Dict[str, List[Pivot]] = {}
    for idx, kappa in enumerate(kappas, start=1):
        key = f"k{int(kappa) if kappa == int(kappa) else kappa}"
        # Map (1.0, 3.0, 9.0) -> (k1, k3, k9) canonically.
        if kappa == 1.0:
            key = "k1"
        elif kappa == 3.0:
            key = "k3"
        elif kappa == 9.0:
            key = "k9"
        result[key] = detect_directional_change(bars, kappa=kappa, atr_period=atr_period)
    return result


def detect_structure_multi_scale(
    bars: Sequence[Any],
    kappas: Tuple[float, ...] = _DEFAULT_KAPPAS,
    atr_period: int = 14,
    cache_symbol: str | None = None,
) -> Dict[str, List[Pivot]]:
    """Run `detect_directional_change` at multiple scales and return a dict
    keyed by `k1`, `k3`, `k9` (or `kN` for custom kappas).

    Cache key = `(symbol, len(bars), last_timestamp, kappas, atr_period)`.
    The caller should pass a stable `cache_symbol` to avoid collisions when
    the same indices/timestamps appear on different instruments.
    """
    if not bars:
        return {f"k{int(k) if k == int(k) else k}": [] for k in kappas}

    last_ts = bars[-1].timestamp
    # Build a hashable OHLC+timestamp tuple. We skip volume to keep the tuple
    # small; zigzag doesn't consult volume.
    bars_tuple = tuple(
        (float(b.open), float(b.high), float(b.low), float(b.close), b.timestamp)
        for b in bars
    )
    cache_key = (cache_symbol, len(bars), last_ts, kappas, atr_period)
    return _cached_multi_scale(cache_key, bars_tuple, kappas, atr_period)


def invalidate_cache() -> None:
    """Test helper — drop the LRU cache."""
    _cached_multi_scale.cache_clear()
