"""Tests for §0.B.3 htf_bias_structure — 7-step HTF bias state machine."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.features.htf_bias_structure import (
    FVGZone,
    HTFBiasInputs,
    HTFBiasResult,
    classify_fvg_respect,
    compute_htf_bias,
    compute_structural_bias,
    detect_close_through_flip,
    is_in_retracement,
    rank_active_draws,
)
from engines.features.pivot import Pivot
from engines.features.pool_freshness_tracker import Pool, PoolKind, PoolTF

ET = ZoneInfo("America/New_York")


def _ts(h: int = 10, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def _piv(kind: str, idx: int, price: float, ts: datetime = _ts()) -> Pivot:
    return Pivot(index=idx, price=price, type=kind, timestamp=ts)


# --- Step 1: compute_structural_bias ---

def test_structural_bias_bullish_HH_HL():
    pivots = [
        _piv("high", 10, 100.0, _ts(8)),
        _piv("low", 20, 97.0, _ts(9)),
        _piv("high", 30, 102.0, _ts(10)),  # HH
        _piv("low", 40, 99.0, _ts(11)),  # HL (99 > 97)
    ]
    bias, pattern, conf = compute_structural_bias(pivots)
    assert bias == "bullish"
    assert pattern == "HH_HL"
    assert conf == 1.0


def test_structural_bias_bearish_LL_LH():
    pivots = [
        _piv("high", 10, 105.0, _ts(8)),
        _piv("low", 20, 100.0, _ts(9)),
        _piv("high", 30, 103.0, _ts(10)),  # LH
        _piv("low", 40, 97.0, _ts(11)),  # LL
    ]
    bias, pattern, conf = compute_structural_bias(pivots)
    assert bias == "bearish"
    assert pattern == "LL_LH"
    assert conf == 1.0


def test_structural_bias_mixed_returns_neutral():
    # HH + LL — mixed (one bull, one bear).
    pivots = [
        _piv("high", 10, 100.0, _ts(8)),
        _piv("low", 20, 99.0, _ts(9)),
        _piv("high", 30, 102.0, _ts(10)),  # HH
        _piv("low", 40, 97.0, _ts(11)),  # LL
    ]
    bias, pattern, conf = compute_structural_bias(pivots)
    assert bias == "neutral"
    assert pattern == "mixed"
    assert conf == 0.3


def test_structural_bias_insufficient_data():
    assert compute_structural_bias([])[0] == "neutral"
    bias, pattern, conf = compute_structural_bias([_piv("high", 1, 100.0)])
    assert pattern == "insufficient"
    assert conf == 0.0


# --- Step 2: is_in_retracement ---

def test_retracement_bullish_when_price_in_discount_half():
    pivots = [
        _piv("low", 10, 100.0, _ts(8)),
        _piv("high", 20, 110.0, _ts(9)),
    ]
    # At 105 (50% of range 100-110) = within [25%, 75%] default band.
    assert is_in_retracement(pivots, 105.0, "bullish") is True
    # At 108 (80%) = above ceiling, not retracement.
    assert is_in_retracement(pivots, 108.0, "bullish") is False


def test_retracement_false_on_neutral_bias():
    pivots = [_piv("low", 10, 100.0), _piv("high", 20, 110.0)]
    assert is_in_retracement(pivots, 105.0, "neutral") is False


# --- Step 3: classify_fvg_respect ---

def test_fvg_respected_when_touch_without_close_through():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
    )
    # Bar touches zone (100-101.5 overlaps) and closes inside.
    state = classify_fvg_respect(zone, bar_high=101.5, bar_low=100.0, bar_close=101.0)
    assert state == "respected"


def test_fvg_closed_through_when_close_below_bullish_zone():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
    )
    # Close below zone → closed_through.
    state = classify_fvg_respect(zone, bar_high=101.5, bar_low=99.0, bar_close=99.5)
    assert state == "closed_through"


def test_fvg_pending_when_no_touch_preserves_state():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
    )
    # Bar doesn't touch zone.
    state = classify_fvg_respect(zone, bar_high=95.0, bar_low=94.0, bar_close=94.5)
    assert state == "pending"


# --- Step 4: rank_active_draws ---

def test_rank_active_draws_preserves_input_order_and_truncates():
    pools = [
        Pool(id="p4h_h", tf=PoolTF.H4.value, kind=PoolKind.HIGH.value,
             price=102.0, created_ts=_ts(9)),
        Pool(id="p1h_h", tf=PoolTF.H1.value, kind=PoolKind.HIGH.value,
             price=101.0, created_ts=_ts(9)),
        Pool(id="p5m_h", tf=PoolTF.M5.value, kind=PoolKind.HIGH.value,
             price=100.5, created_ts=_ts(9)),
    ]
    # Caller responsibility: pre-sort by priority (PoolFreshnessTracker does this).
    ids = rank_active_draws(pools, max_count=2)
    assert ids == ("p4h_h", "p1h_h")


# --- Step 6: detect_close_through_flip ---

def test_flip_detected_when_bullish_fvg_closed_through_and_prior_bullish():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
        state="closed_through",
    )
    flip = detect_close_through_flip(
        prior_bias="bullish", zones=[zone], current_ts=_ts(11)
    )
    assert flip == _ts(11)


def test_no_flip_when_fvg_state_not_closed_through():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
        state="respected",
    )
    assert detect_close_through_flip("bullish", [zone], _ts(11)) is None


def test_no_flip_when_prior_bias_none_or_neutral():
    zone = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(8),
        state="closed_through",
    )
    assert detect_close_through_flip(None, [zone], _ts(11)) is None
    assert detect_close_through_flip("neutral", [zone], _ts(11)) is None


# --- Orchestrator: compute_htf_bias ---

def test_compute_htf_bias_full_bullish_with_smt_confirms_confidence_boost():
    pivots = [
        _piv("high", 10, 100.0, _ts(8)),
        _piv("low", 20, 97.0, _ts(9)),
        _piv("high", 30, 102.0, _ts(10)),
        _piv("low", 40, 99.0, _ts(11)),
    ]
    fvg = FVGZone(
        id="fvg1", low=98.0, high=99.5,
        direction="bullish", created_ts=_ts(10),
    )
    fresh_pools = [
        Pool(id="prevD_h", tf=PoolTF.PREV_D.value, kind=PoolKind.HIGH.value,
             price=105.0, created_ts=_ts(9)),
    ]
    inputs = HTFBiasInputs(
        pivots_k9_htf=pivots,
        last_close_htf=99.5,
        last_high_htf=99.7,
        last_low_htf=98.5,
        fvg_zones_htf=[fvg],
        fresh_draws=fresh_pools,
        premarket_manipulation=False,
        smt_divergence_present=True,
        prior_bias="bullish",
    )
    result = compute_htf_bias(inputs, current_ts=_ts(11))

    assert result.bias == "bullish"
    assert result.structure_pattern == "HH_HL"
    assert result.confidence == pytest.approx(1.0)  # 1.0 + 0.2 capped at 1.0
    assert "fvg1" in result.respected_fvgs
    assert result.active_draws == ("prevD_h",)
    assert result.smt_refinement == "confirms"
    assert result.flipped_at is None


def test_compute_htf_bias_flip_downgrades_confidence():
    """When a closed_through FVG contradicts prior_bias, confidence drops sharply."""
    pivots = [
        _piv("high", 10, 100.0, _ts(8)),
        _piv("low", 20, 97.0, _ts(9)),
        _piv("high", 30, 102.0, _ts(10)),
        _piv("low", 40, 99.0, _ts(11)),
    ]
    fvg = FVGZone(
        id="fvg1", low=100.0, high=102.0,
        direction="bullish", created_ts=_ts(9),
    )
    # Last bar close BELOW the bullish FVG → closed_through.
    inputs = HTFBiasInputs(
        pivots_k9_htf=pivots,
        last_close_htf=99.0,
        last_high_htf=101.0,
        last_low_htf=98.5,
        fvg_zones_htf=[fvg],
        fresh_draws=(),
        premarket_manipulation=False,
        smt_divergence_present=None,
        prior_bias="bullish",
    )
    result = compute_htf_bias(inputs, current_ts=_ts(12))

    assert result.bias == "bullish"  # structural pattern unchanged
    assert result.flipped_at == _ts(12)
    assert "fvg1" in result.closed_through_fvgs
    # Confidence was 1.0, flip drops to 0.3.
    assert result.confidence == pytest.approx(0.3)


def test_compute_htf_bias_neutral_when_insufficient_structure():
    inputs = HTFBiasInputs(
        pivots_k9_htf=[],
        last_close_htf=100.0,
    )
    result = compute_htf_bias(inputs, current_ts=_ts(10))
    assert result.bias == "neutral"
    assert result.structure_pattern == "insufficient"
    assert result.confidence == 0.0
    assert result.smt_refinement is None
