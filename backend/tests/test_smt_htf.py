"""Tests for §0.B.2 smt_htf — cross-index SMT divergence detector."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.features.pivot import Pivot
from engines.patterns.smt_htf import (
    SMTInputs,
    SMTSignal,
    classify_last_pivot,
    detect_smt_divergence,
)

ET = ZoneInfo("America/New_York")


def _ts(h: int, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def _piv(kind: str, idx: int, price: float, ts: datetime) -> Pivot:
    return Pivot(index=idx, price=price, type=kind, timestamp=ts)


# --- classify_last_pivot ---

def test_classify_HH_when_latest_high_above_prior_high():
    pivots = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
        _piv("high", 30, 102.0, _ts(11)),  # HH: 102 > 100
    ]
    assert classify_last_pivot(pivots) == "HH"


def test_classify_LH_when_latest_high_below_prior_high():
    pivots = [
        _piv("high", 10, 105.0, _ts(9)),
        _piv("low", 20, 100.0, _ts(10)),
        _piv("high", 30, 103.0, _ts(11)),  # LH: 103 < 105
    ]
    assert classify_last_pivot(pivots) == "LH"


def test_classify_HL_when_latest_low_above_prior_low():
    pivots = [
        _piv("low", 10, 98.0, _ts(9)),
        _piv("high", 20, 102.0, _ts(10)),
        _piv("low", 30, 100.0, _ts(11)),  # HL: 100 > 98
    ]
    assert classify_last_pivot(pivots) == "HL"


def test_classify_LL_when_latest_low_below_prior_low():
    pivots = [
        _piv("low", 10, 100.0, _ts(9)),
        _piv("high", 20, 102.0, _ts(10)),
        _piv("low", 30, 98.0, _ts(11)),  # LL: 98 < 100
    ]
    assert classify_last_pivot(pivots) == "LL"


def test_classify_none_insufficient_pivots():
    assert classify_last_pivot([]) is None
    assert classify_last_pivot([_piv("high", 1, 100.0, _ts(9))]) is None


def test_classify_none_no_prior_same_type():
    # Latest is "high" but no previous "high" in the list.
    pivots = [
        _piv("low", 10, 98.0, _ts(9)),
        _piv("low", 20, 97.0, _ts(10)),
        _piv("high", 30, 100.0, _ts(11)),
    ]
    assert classify_last_pivot(pivots) is None


def test_classify_since_ts_filters_out_older_pivots():
    pivots = [
        _piv("high", 10, 100.0, _ts(8)),  # before sweep
        _piv("high", 20, 102.0, _ts(9)),  # before sweep
        _piv("high", 30, 101.0, _ts(10)),  # after sweep — only 1 post-sweep high
    ]
    # since_ts=10:00 → only one high pivot → insufficient → None
    assert classify_last_pivot(pivots, since_ts=_ts(10)) is None


# --- detect_smt_divergence ---

def _build_inputs(symbol, last_high_price, last_low_price, prev_high_price, last_close, attached=None):
    """Build SMTInputs with 4 pivots: prev_high, low, high_latest, low_latest order variations."""
    # Ensure we have >= 2 highs so classify_last_pivot works on the "high" tail.
    pivots = [
        _piv("high", 10, prev_high_price, _ts(8)),
        _piv("low", 20, last_low_price, _ts(9)),
        _piv("high", 30, last_high_price, _ts(10)),
    ]
    return SMTInputs(
        symbol=symbol,
        pivots_k3=pivots,
        last_close=last_close,
        attached_swing_price=attached,
    )


def test_bear_divergence_spy_LH_qqq_HH_emits_short_signal_on_qqq():
    """SPY makes LH (leading bearish), QQQ makes HH (lagging) → SHORT QQQ, TP = SPY attached swing."""
    spy = _build_inputs("SPY", last_high_price=99.0, last_low_price=95.0,
                        prev_high_price=100.0, last_close=98.5,
                        attached=92.0)  # attached swing for completion
    qqq = _build_inputs("QQQ", last_high_price=103.0, last_low_price=98.0,
                        prev_high_price=102.0, last_close=102.5,
                        attached=None)  # lagging doesn't need attached

    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    assert signal is not None
    assert signal.leading_symbol == "SPY"
    assert signal.lagging_symbol == "QQQ"
    assert signal.direction == "SHORT"
    assert signal.divergence_type == "bear"
    assert signal.lagging_entry_reference == pytest.approx(102.5)
    assert signal.smt_completion_target == pytest.approx(92.0)


def test_bull_divergence_qqq_HL_spy_LL_emits_long_signal_on_spy():
    """QQQ makes HL (leading bullish), SPY makes LL (lagging) → LONG SPY, TP = QQQ attached swing."""
    spy_pivs = [
        _piv("low", 10, 98.0, _ts(8)),
        _piv("high", 20, 102.0, _ts(9)),
        _piv("low", 30, 96.0, _ts(10)),  # LL: 96 < 98
    ]
    qqq_pivs = [
        _piv("low", 10, 100.0, _ts(8)),
        _piv("high", 20, 104.0, _ts(9)),
        _piv("low", 30, 101.0, _ts(10)),  # HL: 101 > 100
    ]
    spy = SMTInputs(symbol="SPY", pivots_k3=spy_pivs, last_close=96.5,
                    attached_swing_price=None)
    qqq = SMTInputs(symbol="QQQ", pivots_k3=qqq_pivs, last_close=101.5,
                    attached_swing_price=108.0)  # leading attached

    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    assert signal is not None
    assert signal.leading_symbol == "QQQ"
    assert signal.lagging_symbol == "SPY"
    assert signal.direction == "LONG"
    assert signal.divergence_type == "bull"
    assert signal.lagging_entry_reference == pytest.approx(96.5)
    assert signal.smt_completion_target == pytest.approx(108.0)


def test_no_signal_when_both_instruments_HH():
    """Same classification on both sides → no divergence."""
    spy = _build_inputs("SPY", 102.0, 98.0, 100.0, 101.5)
    qqq = _build_inputs("QQQ", 103.0, 98.0, 101.0, 102.5)
    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    assert signal is None


def test_no_signal_when_leading_has_no_attached_swing():
    """Bearish divergence pattern detected but leading has no attached_swing_price → no signal."""
    spy = _build_inputs("SPY", 99.0, 95.0, 100.0, 98.5, attached=None)  # leading without attached
    qqq = _build_inputs("QQQ", 103.0, 98.0, 102.0, 102.5, attached=None)
    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    assert signal is None  # cannot compute TP without attached swing


def test_no_signal_insufficient_pivots_on_one_side():
    spy = _build_inputs("SPY", 99.0, 95.0, 100.0, 98.5, attached=92.0)
    qqq_short = SMTInputs(
        symbol="QQQ",
        pivots_k3=[_piv("high", 1, 103.0, _ts(10))],  # only 1 pivot
        last_close=102.5,
        attached_swing_price=None,
    )
    signal = detect_smt_divergence(a=spy, b=qqq_short, detection_ts=_ts(10, 5))
    assert signal is None


def test_since_ts_filter_post_sweep_only():
    """When sweep_ts is given, pivots before that ts are ignored — requires post-sweep structure."""
    # SPY: pre-sweep high at 9:00, post-sweep low only (not enough to classify highs post-sweep).
    spy_pivs = [
        _piv("high", 10, 100.0, _ts(9, 0)),  # pre-sweep
        _piv("low", 20, 95.0, _ts(10, 30)),  # post-sweep
    ]
    qqq_pivs = [
        _piv("high", 10, 102.0, _ts(9, 0)),  # pre-sweep
        _piv("high", 20, 103.0, _ts(10, 30)),  # post-sweep single high → cannot classify
    ]
    spy = SMTInputs(symbol="SPY", pivots_k3=spy_pivs, last_close=95.5,
                    attached_swing_price=92.0)
    qqq = SMTInputs(symbol="QQQ", pivots_k3=qqq_pivs, last_close=102.5,
                    attached_swing_price=None)
    # With sweep_ts at 10:00, classify_last_pivot post-sweep lacks 2 same-type pivots.
    signal = detect_smt_divergence(
        a=spy, b=qqq, detection_ts=_ts(10, 45), sweep_ts=_ts(10, 0)
    )
    assert signal is None


def test_since_ts_allows_valid_signal_post_sweep():
    """With sufficient post-sweep structure, signal still emits correctly."""
    # Build pivots so that each instrument has 2 same-type pivots post sweep_ts=10:00.
    spy_pivs = [
        _piv("high", 5, 100.0, _ts(9, 30)),  # pre-sweep noise
        _piv("high", 10, 105.0, _ts(10, 5)),  # post-sweep #1
        _piv("low", 15, 100.0, _ts(10, 15)),
        _piv("high", 20, 103.0, _ts(10, 30)),  # post-sweep #2 → LH (103 < 105)
    ]
    qqq_pivs = [
        _piv("high", 5, 98.0, _ts(9, 30)),  # pre-sweep
        _piv("high", 10, 102.0, _ts(10, 5)),  # post-sweep #1
        _piv("low", 15, 99.0, _ts(10, 15)),
        _piv("high", 20, 104.0, _ts(10, 30)),  # post-sweep #2 → HH (104 > 102)
    ]
    spy = SMTInputs(symbol="SPY", pivots_k3=spy_pivs, last_close=102.5,
                    attached_swing_price=98.0)
    qqq = SMTInputs(symbol="QQQ", pivots_k3=qqq_pivs, last_close=103.5,
                    attached_swing_price=None)

    signal = detect_smt_divergence(
        a=spy, b=qqq, detection_ts=_ts(10, 45), sweep_ts=_ts(10, 0)
    )
    assert signal is not None
    assert signal.leading_symbol == "SPY"
    assert signal.lagging_symbol == "QQQ"
    assert signal.direction == "SHORT"
    assert signal.divergence_type == "bear"
    assert signal.lead_pivot_price == pytest.approx(103.0)
    assert signal.prev_same_type_pivot_price == pytest.approx(105.0)


def test_mixed_pattern_not_canonical_smt_returns_none():
    """Patterns outside {LH/HH, HL/LL} are not canon SMT — no signal."""
    # SPY: HL (bullish low), QQQ: HH (bullish high) — both bullish-biased, not divergent.
    spy_pivs = [
        _piv("low", 10, 98.0, _ts(9)),
        _piv("high", 20, 102.0, _ts(10)),
        _piv("low", 30, 100.0, _ts(11)),  # HL
    ]
    qqq_pivs = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
        _piv("high", 30, 102.0, _ts(11)),  # HH
    ]
    spy = SMTInputs("SPY", spy_pivs, last_close=100.5, attached_swing_price=95.0)
    qqq = SMTInputs("QQQ", qqq_pivs, last_close=101.5, attached_swing_price=None)
    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(11, 5))
    assert signal is None


def test_close_through_invalidation_not_in_scope_but_no_crash_on_edge_case():
    """Edge-case inputs (equal pivot prices) should not crash.

    When the latest high equals the previous high, classify_last_pivot falls
    through to LH (strict > test), documenting conservative bias — not a HH.
    """
    pivots = [
        _piv("high", 10, 100.0, _ts(9)),
        _piv("low", 20, 98.0, _ts(10)),
        _piv("high", 30, 100.0, _ts(11)),  # equal to prev → treated as LH (not HH)
    ]
    assert classify_last_pivot(pivots) == "LH"


def test_symmetry_swap_a_and_b_produces_same_signal():
    """Swapping a and b should not change the signal semantics (leading/lagging are identified)."""
    spy = _build_inputs("SPY", 99.0, 95.0, 100.0, 98.5, attached=92.0)  # LH (leading)
    qqq = _build_inputs("QQQ", 103.0, 98.0, 102.0, 102.5, attached=None)  # HH (lagging)

    sig_ab = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    sig_ba = detect_smt_divergence(a=qqq, b=spy, detection_ts=_ts(10, 5))

    assert sig_ab is not None and sig_ba is not None
    assert sig_ab.leading_symbol == sig_ba.leading_symbol == "SPY"
    assert sig_ab.lagging_symbol == sig_ba.lagging_symbol == "QQQ"
    assert sig_ab.direction == sig_ba.direction == "SHORT"
    assert sig_ab.smt_completion_target == sig_ba.smt_completion_target == pytest.approx(92.0)


def test_signal_fields_complete_and_immutable():
    """Returned SMTSignal should be a frozen dataclass with all required fields."""
    spy = _build_inputs("SPY", 99.0, 95.0, 100.0, 98.5, attached=92.0)
    qqq = _build_inputs("QQQ", 103.0, 98.0, 102.0, 102.5, attached=None)
    signal = detect_smt_divergence(a=spy, b=qqq, detection_ts=_ts(10, 5))
    assert signal is not None
    # Required fields populated.
    assert signal.detected_ts == _ts(10, 5)
    assert signal.lead_pivot_price == pytest.approx(99.0)
    assert signal.prev_same_type_pivot_price == pytest.approx(100.0)
    # Immutability.
    with pytest.raises((AttributeError, Exception)):
        signal.direction = "LONG"  # frozen dataclass raises FrozenInstanceError
