"""Tests for SMT Cross-Index Tracker — §0.5bis entrée #1 state machine."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.features.smt_cross_index_tracker import (
    SMTCrossIndexTracker,
    SMTSetupCandidate,
    SMTState,
    TrackerOutput,
)
from engines.patterns.smt_htf import SMTSignal

ET = ZoneInfo("America/New_York")


def _ts(h: int, m: int = 0, d: int = 17) -> datetime:
    return datetime(2025, 11, d, h, m, tzinfo=ET)


def _mk_signal(detected_ts: datetime, direction: str = "SHORT",
               divergence_type: str = "bear") -> SMTSignal:
    return SMTSignal(
        detected_ts=detected_ts,
        leading_symbol="SPY",
        lagging_symbol="QQQ",
        direction=direction,  # type: ignore
        divergence_type=divergence_type,  # type: ignore
        lagging_entry_reference=102.5,
        smt_completion_target=92.0,
        lead_pivot_price=99.0,
        lead_pivot_ts=detected_ts,
        prev_same_type_pivot_price=100.0,
    )


def test_initial_state_is_idle():
    t = SMTCrossIndexTracker()
    assert t.state == SMTState.IDLE
    assert t.pool_sweep_ts is None


def test_pool_sweep_4h_arms_pool_sweeped_state():
    t = SMTCrossIndexTracker()
    sweep_ts = _ts(10, 0)
    t.on_pool_sweeps(swept_pool_ids=["4h_high_123"], symbol="SPY", tf="4h", bar_ts=sweep_ts)
    assert t.state == SMTState.POOL_SWEEPED
    assert t.pool_sweep_ts == sweep_ts


def test_pool_sweep_5m_does_not_arm():
    """Only HTF pools (4h/1h) arm the tracker. 5m sweep ignored."""
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["5m_high_123"], symbol="SPY", tf="5m", bar_ts=_ts(10, 0))
    assert t.state == SMTState.IDLE


def test_pool_sweep_wrong_symbol_does_not_arm():
    """Sweep on a symbol outside the pair is ignored."""
    t = SMTCrossIndexTracker(pair=("SPY", "QQQ"))
    t.on_pool_sweeps(swept_pool_ids=["4h_high_123"], symbol="IWM", tf="4h", bar_ts=_ts(10, 0))
    assert t.state == SMTState.IDLE


def test_signal_progression_to_smt_emitted():
    """Full happy path : IDLE → POOL_SWEEPED → STRUCTURE_OBSERVABLE → SMT_SIGNAL_EMITTED."""
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.advance_to_structure_observable(_ts(10, 20))
    assert t.state == SMTState.STRUCTURE_OBSERVABLE

    sig = _mk_signal(_ts(10, 30))
    t.on_signal(sig, _ts(10, 30))
    assert t.state == SMTState.SMT_SIGNAL_EMITTED


def test_signal_ignored_when_pair_mismatch():
    """A signal involving a symbol outside the pair is rejected."""
    t = SMTCrossIndexTracker(pair=("SPY", "QQQ"))
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.advance_to_structure_observable(_ts(10, 20))
    bad_sig = SMTSignal(
        detected_ts=_ts(10, 30),
        leading_symbol="IWM",  # not in pair
        lagging_symbol="QQQ",
        direction="SHORT",  # type: ignore
        divergence_type="bear",  # type: ignore
        lagging_entry_reference=102.5,
        smt_completion_target=92.0,
        lead_pivot_price=99.0,
        lead_pivot_ts=_ts(10, 30),
        prev_same_type_pivot_price=100.0,
    )
    t.on_signal(bad_sig, _ts(10, 30))
    assert t.state == SMTState.STRUCTURE_OBSERVABLE  # unchanged


def test_emit_setup_requires_all_gates_passing():
    """All 4 gates must pass for EMIT_SETUP. Any failure keeps state in SMT_SIGNAL_EMITTED."""
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.advance_to_structure_observable(_ts(10, 20))
    t.on_signal(_mk_signal(_ts(10, 30)), _ts(10, 30))

    # HTF bias not aligned → no emission.
    out = t.try_emit_setup(
        bar_ts=_ts(10, 31),
        htf_bias_aligned=False,
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
        pre_sweep_gate_pass=True,
    )
    assert out.setup is None
    assert out.state == SMTState.SMT_SIGNAL_EMITTED
    assert out.reason == "gates_pending"

    # All 4 pass → emission.
    out = t.try_emit_setup(
        bar_ts=_ts(10, 32),
        htf_bias_aligned=True,
        macro_kill_zone_pass=True,
        daily_profile_allowed=True,
        pre_sweep_gate_pass=True,
    )
    assert out.setup is not None
    assert out.state == SMTState.EMIT_SETUP
    assert out.setup.symbol == "QQQ"  # lagging
    assert out.setup.direction == "SHORT"
    assert out.setup.smt_completion_price == pytest.approx(92.0)
    assert out.setup.pool_sweep_tf == "4h"


def test_timeout_pool_sweeped_resets_to_idle():
    """POOL_SWEEPED times out after 150 min → reset IDLE with reason."""
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    # Tick at 10:00 (same bar)  — prime trading_date.
    t.on_bar_tick(_ts(10, 0))
    assert t.state == SMTState.POOL_SWEEPED
    # Tick past the 150-min timeout.
    out = t.on_bar_tick(_ts(12, 31))  # 151 min later
    assert out.state == SMTState.IDLE
    assert out.reason == "timeout_POOL_SWEEPED"


def test_timeout_smt_signal_emitted_resets_to_idle():
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.on_bar_tick(_ts(10, 0))
    t.advance_to_structure_observable(_ts(10, 20))
    t.on_signal(_mk_signal(_ts(10, 30)), _ts(10, 30))
    t.on_bar_tick(_ts(10, 30))
    assert t.state == SMTState.SMT_SIGNAL_EMITTED

    # 6-bar 5m timeout = 30 min. Tick at 11:01 (31 min later).
    out = t.on_bar_tick(_ts(11, 1))
    assert out.state == SMTState.IDLE
    assert out.reason == "timeout_SMT_SIGNAL_EMITTED"


def test_trading_day_rollover_resets_tracker():
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.on_bar_tick(_ts(10, 0))
    # Cross the 18:00 ET rollover (next trading date).
    out = t.on_bar_tick(_ts(18, 5))
    assert out.state == SMTState.IDLE
    assert out.reason == "trading_day_rollover"


def test_reset_after_emit_returns_to_idle_preserves_trading_date():
    t = SMTCrossIndexTracker()
    t.on_pool_sweeps(swept_pool_ids=["4h_high_x"], symbol="SPY", tf="4h", bar_ts=_ts(10, 0))
    t.on_bar_tick(_ts(10, 0))
    t.advance_to_structure_observable(_ts(10, 20))
    t.on_signal(_mk_signal(_ts(10, 30)), _ts(10, 30))
    out = t.try_emit_setup(
        bar_ts=_ts(10, 32),
        htf_bias_aligned=True, macro_kill_zone_pass=True,
        daily_profile_allowed=True, pre_sweep_gate_pass=True,
    )
    assert out.state == SMTState.EMIT_SETUP

    t.reset_after_emit()
    assert t.state == SMTState.IDLE

    # Another sweep in the same trading day should arm normally.
    t.on_pool_sweeps(swept_pool_ids=["4h_high_y"], symbol="SPY", tf="4h", bar_ts=_ts(11, 0))
    assert t.state == SMTState.POOL_SWEEPED


def test_on_pool_sweeps_ignored_when_already_armed():
    """Linear state machine : second sweep while POOL_SWEEPED is ignored."""
    t = SMTCrossIndexTracker()
    first = _ts(10, 0)
    t.on_pool_sweeps(swept_pool_ids=["4h_high_1"], symbol="SPY", tf="4h", bar_ts=first)
    assert t.pool_sweep_ts == first
    t.on_pool_sweeps(swept_pool_ids=["4h_high_2"], symbol="QQQ", tf="4h", bar_ts=_ts(10, 15))
    # First sweep preserved.
    assert t.pool_sweep_ts == first
