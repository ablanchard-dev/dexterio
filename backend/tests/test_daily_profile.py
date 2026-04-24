"""Tests for §0.B.6 daily_profile — 3-profile session classification."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from engines.features.daily_profile import (
    SessionProfileSnapshot,
    classify_session_profile,
    is_profile_allowed,
)


@dataclass
class Bar:
    open: float
    high: float
    low: float
    close: float


def _bars(opens_closes_highs_lows):
    """Build bars from a list of (o, h, l, c) tuples."""
    return [Bar(*t) for t in opens_closes_highs_lows]


def test_consolidation_tight_range_and_small_directional_move():
    """Range 100-101, close ≈ open → consolidation."""
    bars = _bars([
        (100.0, 100.8, 99.9, 100.2),  # open
        (100.2, 100.9, 99.95, 100.3),
        (100.3, 100.85, 100.0, 100.1),
        (100.1, 100.7, 100.0, 100.05),  # close
    ])
    result = classify_session_profile(bars, atr=2.0)  # atr 2 → range 1 < 1.5×2=3 tight
    assert result.profile == "consolidation"
    assert result.confidence == pytest.approx(0.7)


def test_manipulation_reversal_up_then_down():
    """First half pushes high, second half reverses below open → manipulation_reversal (down)."""
    bars = _bars([
        (100.0, 102.5, 99.5, 102.0),  # first-half push up (extreme 102.5)
        (102.0, 102.8, 101.5, 102.3),  # continued push
        (102.3, 102.4, 100.0, 100.5),  # reversal begins
        (100.5, 100.8, 98.5, 99.0),   # close below open → reversal down
    ])
    result = classify_session_profile(bars, atr=1.0)
    assert result.profile == "manipulation_reversal"
    assert result.reversal_direction == "down"
    assert result.manipulation_extreme == pytest.approx(102.8)
    assert result.confidence == pytest.approx(0.8)


def test_manipulation_reversal_down_then_up():
    """First half pushes low, second half reverses above open → manipulation_reversal (up)."""
    bars = _bars([
        (100.0, 100.5, 97.0, 97.5),
        (97.5, 98.0, 96.5, 97.0),
        (97.0, 99.0, 97.0, 98.5),
        (98.5, 102.5, 98.0, 102.0),  # close above open → reversal up
    ])
    result = classify_session_profile(bars, atr=1.0)
    assert result.profile == "manipulation_reversal"
    assert result.reversal_direction == "up"
    assert result.manipulation_extreme == pytest.approx(96.5)


def test_continuation_when_prev_is_manip_reversal_same_direction():
    """Today's manip_reversal down + prev manip_reversal down → continuation."""
    prev = SessionProfileSnapshot(
        profile="manipulation_reversal",
        confidence=0.8,
        session_open=100.0, session_close=98.0,
        session_high=103.0, session_low=97.0,
        manipulation_extreme=103.0,
        reversal_direction="down",
    )
    today_bars = _bars([
        (100.0, 102.5, 99.5, 102.0),
        (102.0, 102.8, 101.5, 102.3),
        (102.3, 102.4, 100.0, 100.5),
        (100.5, 100.8, 98.5, 99.0),
    ])
    result = classify_session_profile(today_bars, prev_profile=prev, atr=1.0)
    assert result.profile == "manipulation_reversal_continuation"
    assert result.reversal_direction == "down"


def test_no_continuation_when_prev_direction_differs():
    """Today manip down but prev reversal_direction was up → just manip_reversal, not continuation."""
    prev = SessionProfileSnapshot(
        profile="manipulation_reversal",
        confidence=0.8,
        session_open=100.0, session_close=102.0,
        session_high=103.0, session_low=97.0,
        manipulation_extreme=97.0,
        reversal_direction="up",  # different from today's down
    )
    today_bars = _bars([
        (100.0, 102.5, 99.5, 102.0),
        (102.0, 102.8, 101.5, 102.3),
        (102.3, 102.4, 100.0, 100.5),
        (100.5, 100.8, 98.5, 99.0),
    ])
    result = classify_session_profile(today_bars, prev_profile=prev, atr=1.0)
    assert result.profile == "manipulation_reversal"  # not continuation
    assert result.reversal_direction == "down"


def test_undetermined_when_insufficient_bars():
    bars = _bars([(100.0, 101.0, 99.0, 100.5)])  # only 1 bar
    result = classify_session_profile(bars, atr=1.0)
    assert result.profile == "undetermined"


def test_undetermined_neither_consolidation_nor_manipulation():
    """Clean uptrend without a first-half extreme wick → undetermined."""
    bars = _bars([
        (100.0, 100.5, 100.0, 100.3),  # low == open, no manipulation wick
        (100.3, 101.0, 100.2, 100.8),
        (100.8, 101.5, 100.7, 101.3),
        (101.3, 102.5, 101.2, 102.3),  # straight trend, no manipulation
    ])
    result = classify_session_profile(bars, atr=3.0)  # wide atr → not consolidation
    assert result.profile == "undetermined"


def test_is_profile_allowed_helper():
    assert is_profile_allowed("manipulation_reversal", ["manipulation_reversal", "manipulation_reversal_continuation"]) is True
    assert is_profile_allowed("consolidation", ["manipulation_reversal"]) is False
    assert is_profile_allowed("undetermined", []) is False


def test_prev_profile_ignored_when_profile_is_not_manip_reversal():
    """Even if prev is manip_reversal, today's consolidation classification wins (no continuation)."""
    prev = SessionProfileSnapshot(
        profile="manipulation_reversal",
        confidence=0.8,
        session_open=100.0, session_close=98.0,
        session_high=103.0, session_low=97.0,
        manipulation_extreme=103.0,
        reversal_direction="down",
    )
    # Today is consolidation.
    today_bars = _bars([
        (100.0, 100.5, 99.9, 100.2),
        (100.2, 100.6, 99.95, 100.3),
        (100.3, 100.55, 100.0, 100.1),
        (100.1, 100.5, 100.0, 100.05),
    ])
    result = classify_session_profile(today_bars, prev_profile=prev, atr=2.0)
    assert result.profile == "consolidation"


def test_atr_zero_disables_tight_range_check_for_consolidation():
    """With atr=0 fallback, only directional-move test is used for consolidation."""
    # Range 100-105 but directional move tiny → classified as consolidation under atr=0.
    bars = _bars([
        (100.0, 105.0, 99.0, 100.5),
        (100.5, 104.5, 99.5, 100.3),
        (100.3, 103.0, 99.8, 100.2),
        (100.2, 102.0, 99.5, 100.1),  # close ≈ open, large range
    ])
    result = classify_session_profile(bars, atr=0.0)
    assert result.profile == "consolidation"
