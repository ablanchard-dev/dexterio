"""Tests for §0.B.4 equilibrium_zone — EQ most-recent swing."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.features.equilibrium_zone import (
    EquilibriumZone,
    bar_taps_equilibrium,
    compute_equilibrium_zone,
)
from engines.features.pivot import Pivot

ET = ZoneInfo("America/New_York")


def _ts(h: int, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def _piv(kind: str, idx: int, price: float, ts: datetime) -> Pivot:
    return Pivot(index=idx, price=price, type=kind, timestamp=ts)


def test_compute_eq_mid_of_most_recent_high_and_low():
    pivots = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
    ]
    zone = compute_equilibrium_zone(pivots)
    assert zone is not None
    assert zone.level == pytest.approx(99.0)
    assert zone.last_swing_H_price == 100.0
    assert zone.last_swing_L_price == 98.0
    assert zone.active is True


def test_compute_eq_redraws_on_new_higher_high():
    """New HH → EQ should shift upward (uses the new high, not the old)."""
    pivots_old = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
    ]
    old = compute_equilibrium_zone(pivots_old)
    assert old is not None and old.level == pytest.approx(99.0)

    pivots_new = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
        _piv("high", 30, 104.0, _ts(11)),  # HH
    ]
    new = compute_equilibrium_zone(pivots_new)
    assert new is not None
    # Uses most-recent high=104 and most-recent low=98 → EQ=101.
    assert new.level == pytest.approx(101.0)
    assert new.last_swing_H_price == 104.0


def test_compute_eq_redraws_on_new_lower_low():
    pivots = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
        _piv("low", 30, 94.0, _ts(11)),  # LL
    ]
    zone = compute_equilibrium_zone(pivots)
    assert zone is not None
    # Most-recent high=100, most-recent low=94 → EQ=97.
    assert zone.level == pytest.approx(97.0)


def test_compute_eq_none_when_missing_low_or_high():
    only_highs = [_piv("high", 10, 100.0, _ts(9))]
    assert compute_equilibrium_zone(only_highs) is None

    only_lows = [_piv("low", 10, 98.0, _ts(9)), _piv("low", 20, 96.0, _ts(10))]
    assert compute_equilibrium_zone(only_lows) is None

    assert compute_equilibrium_zone([]) is None


def test_bar_taps_equilibrium_within_tolerance_band():
    zone = EquilibriumZone(
        level=100.0, last_swing_H_price=102.0, last_swing_L_price=98.0,
        last_swing_H_ts=_ts(9), last_swing_L_ts=_ts(10), active=True,
    )
    # atr=1.0, tolerance=0.25 → half_band=0.25 → band [99.75, 100.25]
    # Bar low=99.5, high=99.7 → bar_high(99.7) < band_lo(99.75) → no overlap.
    assert bar_taps_equilibrium(zone, bar_high=99.7, bar_low=99.5, atr=1.0, tolerance_atr=0.25) is False

    # Bar [99.9, 100.1] → overlaps band.
    assert bar_taps_equilibrium(zone, bar_high=100.1, bar_low=99.9, atr=1.0, tolerance_atr=0.25) is True

    # Exact-level touch.
    assert bar_taps_equilibrium(zone, bar_high=100.0, bar_low=99.95, atr=1.0, tolerance_atr=0.25) is True


def test_bar_taps_equilibrium_false_when_zone_inactive():
    zone = EquilibriumZone(
        level=100.0, last_swing_H_price=102.0, last_swing_L_price=98.0,
        last_swing_H_ts=_ts(9), last_swing_L_ts=_ts(10), active=False,
    )
    assert bar_taps_equilibrium(zone, bar_high=100.0, bar_low=99.9, atr=1.0) is False


def test_bar_taps_equilibrium_falls_back_to_exact_when_atr_zero():
    """ATR=0 or tolerance=0 → strict bar contains level."""
    zone = EquilibriumZone(
        level=100.0, last_swing_H_price=102.0, last_swing_L_price=98.0,
        last_swing_H_ts=_ts(9), last_swing_L_ts=_ts(10), active=True,
    )
    # Bar [100.0, 100.5] contains level=100.0 → True.
    assert bar_taps_equilibrium(zone, bar_high=100.5, bar_low=100.0, atr=0.0, tolerance_atr=0.25) is True
    # Bar [99.5, 99.9] does not contain level=100.0 → False.
    assert bar_taps_equilibrium(zone, bar_high=99.9, bar_low=99.5, atr=0.0, tolerance_atr=0.25) is False


def test_compute_eq_handles_interleaved_pivots_takes_most_recent_of_each():
    """Pivots in arbitrary interleaved order — take most-recent of each type."""
    pivots = [
        _piv("high", 10, 105.0, _ts(8)),
        _piv("high", 20, 100.0, _ts(9)),  # older-most-recent high
        _piv("low", 30, 97.0, _ts(10)),
        _piv("low", 40, 95.0, _ts(11)),  # most-recent low
    ]
    zone = compute_equilibrium_zone(pivots)
    assert zone is not None
    # Most-recent high=100 (idx 20), most-recent low=95 (idx 40) → EQ=97.5.
    assert zone.level == pytest.approx(97.5)
    assert zone.last_swing_H_price == 100.0
    assert zone.last_swing_L_price == 95.0


def test_compute_eq_propagates_last_tap_ts():
    pivots = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
    ]
    tap_ts = _ts(11, 30)
    zone = compute_equilibrium_zone(pivots, last_tap_ts=tap_ts)
    assert zone is not None
    assert zone.last_tap_ts == tap_ts
