"""Tests for SMTDriver — orchestrator bridging SMTCrossIndexTracker → ICTPattern."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.features.htf_bias_structure import HTFBiasResult
from engines.features.pivot import Pivot
from engines.features.smt_cross_index_tracker import SMTState
from engines.smt_driver import SMTDriver

ET = ZoneInfo("America/New_York")


def _ts(h: int, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def _piv(kind: str, idx: int, price: float, ts: datetime) -> Pivot:
    return Pivot(index=idx, price=price, type=kind, timestamp=ts)


@dataclass
class Bar:
    high: float
    low: float
    close: float


def _bias(bias_str: str) -> HTFBiasResult:
    return HTFBiasResult(
        bias=bias_str,  # type: ignore
        confidence=1.0 if bias_str != "neutral" else 0.0,
        structure_pattern="HH_HL" if bias_str == "bullish" else "LL_LH",
        in_retracement=False,
        respected_fvgs=(), disrespected_fvgs=(), closed_through_fvgs=(),
        active_draws=(),
        premarket_manipulation_detected=False,
        flipped_at=None,
        smt_refinement=None,
    )


def test_driver_initial_state():
    d = SMTDriver(pair=("SPY", "QQQ"))
    assert d.state == SMTState.IDLE
    assert d.emit_count == 0
    assert d.last_emission is None


def test_driver_htf_pool_bootstrap_registers_high_and_low():
    d = SMTDriver()
    d.on_htf_bar_close(
        symbol="SPY", tf="4h",
        bar_high=450.0, bar_low=440.0, bar_close_ts=_ts(6, 0),
    )
    # Pools registered in the internal freshness tracker.
    assert len(d._freshness["SPY"]) == 2


def test_driver_ignores_htf_register_for_wrong_tf_or_symbol():
    d = SMTDriver(pair=("SPY", "QQQ"))
    d.on_htf_bar_close(
        symbol="IWM", tf="4h", bar_high=200.0, bar_low=195.0,
        bar_close_ts=_ts(6, 0),
    )
    d.on_htf_bar_close(
        symbol="SPY", tf="5m", bar_high=450.0, bar_low=440.0,
        bar_close_ts=_ts(6, 0),
    )
    assert len(d._freshness["SPY"]) == 0
    # QQQ tracker never touched.
    assert len(d._freshness["QQQ"]) == 0


def test_driver_end_to_end_bearish_divergence_emits_synthetic_pattern():
    """Happy path : HTF pools registered, SPY sweeps its 4h high, then post-sweep
    divergence (SPY LH, QQQ HH) → SMT signal → all gates pass → ICTPattern emitted."""
    d = SMTDriver(pair=("SPY", "QQQ"), pre_sweep_window_minutes=30)

    # Bootstrap HTF pools at 06:00 ET.
    d.on_htf_bar_close("SPY", "4h", bar_high=450.0, bar_low=440.0, bar_close_ts=_ts(6, 0))
    d.on_htf_bar_close("QQQ", "4h", bar_high=510.0, bar_low=495.0, bar_close_ts=_ts(6, 0))

    # --- Bar 1 : 10:00 ET, SPY sweeps 4h high at 450 → POOL_SWEEPED ---
    emission = d.on_5m_bar(
        bar_ts=_ts(10, 0),
        symbol_bars={"SPY": Bar(high=450.50, low=449.0, close=450.30),
                     "QQQ": Bar(high=505.0, low=503.0, close=504.0)},
        pivots_k3={"SPY": [], "QQQ": []},  # no pivots yet
        last_closes={"SPY": 450.30, "QQQ": 504.0},
        attached_swing_prices={"SPY": 440.5, "QQQ": None},
        htf_bias={"SPY": _bias("bullish"), "QQQ": _bias("bullish")},
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
    )
    assert emission is None
    assert d.state == SMTState.POOL_SWEEPED

    # --- Bar 2 : 10:05 ET, enough post-sweep structure emerges ---
    # SPY : LH (99<100), QQQ : HH (104>102)
    emission = d.on_5m_bar(
        bar_ts=_ts(10, 5),
        symbol_bars={"SPY": Bar(high=449.0, low=447.5, close=448.0),
                     "QQQ": Bar(high=506.0, low=504.5, close=505.5)},
        pivots_k3={
            "SPY": [
                _piv("high", 100, 100.0, _ts(10, 2)),
                _piv("low", 102, 97.0, _ts(10, 3)),
                _piv("high", 103, 99.0, _ts(10, 4)),  # LH
            ],
            "QQQ": [
                _piv("high", 100, 102.0, _ts(10, 2)),
                _piv("low", 102, 100.0, _ts(10, 3)),
                _piv("high", 103, 104.0, _ts(10, 4)),  # HH
            ],
        },
        last_closes={"SPY": 99.0, "QQQ": 103.8},
        attached_swing_prices={"SPY": 95.5, "QQQ": None},
        htf_bias={"SPY": _bias("bullish"), "QQQ": _bias("bullish")},
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
    )

    # After this bar, tracker should have transitioned through
    # STRUCTURE_OBSERVABLE → SMT_SIGNAL_EMITTED → EMIT_SETUP in one tick,
    # producing a synthetic ICTPattern.
    assert emission is not None
    assert emission.symbol == "QQQ"  # lagging
    assert emission.direction == "bearish"  # SHORT
    assert emission.pattern_type == "smt_cross_index_sequence"
    assert emission.price_level == pytest.approx(103.8)
    assert emission.details["smt_completion_target"] == pytest.approx(95.5)
    assert emission.details["leading_symbol"] == "SPY"
    assert emission.details["pool_sweep_tf"] == "4h"
    assert emission.strength == 1.0
    assert emission.confidence == 0.95

    assert d.emit_count == 1
    assert d.last_emission is emission

    # Consume emission to allow retrigger.
    d.consume_emission()
    assert d.state == SMTState.IDLE


def test_driver_no_emission_when_bias_neutral():
    """HTF bias neutral → _is_bias_aligned_for_signal returns False → no emission."""
    d = SMTDriver()
    d.on_htf_bar_close("SPY", "4h", 450.0, 440.0, _ts(6, 0))

    # Sweep SPY 4h high.
    d.on_5m_bar(
        bar_ts=_ts(10, 0),
        symbol_bars={"SPY": Bar(450.50, 449.0, 450.30),
                     "QQQ": Bar(505.0, 503.0, 504.0)},
        pivots_k3={"SPY": [], "QQQ": []},
        last_closes={"SPY": 450.30, "QQQ": 504.0},
        attached_swing_prices={"SPY": 440.5, "QQQ": None},
        htf_bias={"SPY": _bias("neutral"), "QQQ": _bias("neutral")},
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
    )
    # Structure + divergence emerge.
    emission = d.on_5m_bar(
        bar_ts=_ts(10, 5),
        symbol_bars={"SPY": Bar(449.0, 447.5, 448.0),
                     "QQQ": Bar(506.0, 504.5, 505.5)},
        pivots_k3={
            "SPY": [
                _piv("high", 100, 100.0, _ts(10, 2)),
                _piv("low", 102, 97.0, _ts(10, 3)),
                _piv("high", 103, 99.0, _ts(10, 4)),
            ],
            "QQQ": [
                _piv("high", 100, 102.0, _ts(10, 2)),
                _piv("low", 102, 100.0, _ts(10, 3)),
                _piv("high", 103, 104.0, _ts(10, 4)),
            ],
        },
        last_closes={"SPY": 99.0, "QQQ": 103.8},
        attached_swing_prices={"SPY": 95.5, "QQQ": None},
        htf_bias={"SPY": _bias("neutral"), "QQQ": _bias("neutral")},
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
    )
    # Neutral leading bias → no emission.
    assert emission is None
    # Tracker should be in SMT_SIGNAL_EMITTED (waiting for gates).
    assert d.state == SMTState.SMT_SIGNAL_EMITTED


def test_driver_no_emission_when_macro_kill_zone_fails():
    d = SMTDriver()
    d.on_htf_bar_close("SPY", "4h", 450.0, 440.0, _ts(6, 0))
    d.on_5m_bar(
        bar_ts=_ts(10, 0),
        symbol_bars={"SPY": Bar(450.50, 449.0, 450.30),
                     "QQQ": Bar(505.0, 503.0, 504.0)},
        pivots_k3={"SPY": [], "QQQ": []},
        last_closes={"SPY": 450.30, "QQQ": 504.0},
        attached_swing_prices={"SPY": 440.5, "QQQ": None},
        htf_bias={"SPY": _bias("bullish"), "QQQ": _bias("bullish")},
        macro_kill_zone_pass=False,  # failed
        daily_profile_allowed=True,
    )
    emission = d.on_5m_bar(
        bar_ts=_ts(10, 5),
        symbol_bars={"SPY": Bar(449.0, 447.5, 448.0),
                     "QQQ": Bar(506.0, 504.5, 505.5)},
        pivots_k3={
            "SPY": [
                _piv("high", 100, 100.0, _ts(10, 2)),
                _piv("low", 102, 97.0, _ts(10, 3)),
                _piv("high", 103, 99.0, _ts(10, 4)),
            ],
            "QQQ": [
                _piv("high", 100, 102.0, _ts(10, 2)),
                _piv("low", 102, 100.0, _ts(10, 3)),
                _piv("high", 103, 104.0, _ts(10, 4)),
            ],
        },
        last_closes={"SPY": 99.0, "QQQ": 103.8},
        attached_swing_prices={"SPY": 95.5, "QQQ": None},
        htf_bias={"SPY": _bias("bullish"), "QQQ": _bias("bullish")},
        macro_kill_zone_pass=False,
        daily_profile_allowed=True,
    )
    assert emission is None


def test_driver_reset_clears_state_and_counters():
    d = SMTDriver()
    d.on_htf_bar_close("SPY", "4h", 450.0, 440.0, _ts(6, 0))
    assert len(d._freshness["SPY"]) == 2
    d.reset()
    assert len(d._freshness["SPY"]) == 0
    assert d.state == SMTState.IDLE
    assert d.emit_count == 0
