"""Tests for PairSpreadTracker (Sprint 3, phase D2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.engines.stat_arb.tracker import (
    STATE_ARMED_LONG,
    STATE_ARMED_SHORT,
    STATE_IDLE,
    PairSpreadTracker,
)


def _ts(year=2025, month=11, day=17, hour=14, minute=30):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_threshold_validation():
    with pytest.raises(ValueError):
        PairSpreadTracker(entry_z=0.5, exit_z=0.5)
    with pytest.raises(ValueError):
        PairSpreadTracker(entry_z=2.0, blowout_z=2.0)


def test_idle_emits_no_setup_below_threshold():
    t = PairSpreadTracker(entry_z=2.0, exit_z=0.5, blowout_z=3.0)
    out = t.on_5m_close(ts=_ts(), z=1.5, beta=1.0, is_cointegrated=True)
    assert out is None
    assert t.state == STATE_IDLE


def test_arms_long_on_negative_extreme_z():
    t = PairSpreadTracker(entry_z=2.0, exit_z=0.5, blowout_z=3.0)
    out = t.on_5m_close(ts=_ts(), z=-2.1, beta=1.2, is_cointegrated=True)
    assert out is not None
    assert out["direction"] == "long"
    assert out["armed_z"] == pytest.approx(-2.1)
    assert out["armed_beta"] == pytest.approx(1.2)
    assert t.state == STATE_ARMED_LONG


def test_arms_short_on_positive_extreme_z():
    t = PairSpreadTracker(entry_z=2.0, exit_z=0.5, blowout_z=3.0)
    out = t.on_5m_close(ts=_ts(), z=2.3, beta=1.0, is_cointegrated=True)
    assert out is not None
    assert out["direction"] == "short"
    assert t.state == STATE_ARMED_SHORT


def test_gate_blocks_when_cointegration_fails():
    t = PairSpreadTracker(require_cointegration=True)
    out = t.on_5m_close(ts=_ts(), z=-2.5, beta=1.0, is_cointegrated=False)
    assert out is None
    assert t.state == STATE_IDLE


def test_gate_allows_when_require_cointegration_disabled():
    t = PairSpreadTracker(require_cointegration=False)
    out = t.on_5m_close(ts=_ts(), z=-2.5, beta=1.0, is_cointegrated=False)
    assert out is not None


def test_armed_state_does_not_re_emit():
    t = PairSpreadTracker()
    out1 = t.on_5m_close(ts=_ts(minute=30), z=-2.5, beta=1.0, is_cointegrated=True)
    assert out1 is not None
    out2 = t.on_5m_close(ts=_ts(minute=35), z=-2.5, beta=1.0, is_cointegrated=True)
    assert out2 is None  # already armed


def test_lockout_after_trade_close_blocks_re_entry():
    t = PairSpreadTracker(entry_z=2.0, lockout_bars=3)
    out = t.on_5m_close(ts=_ts(minute=30), z=-2.5, beta=1.0, is_cointegrated=True)
    assert out is not None
    t.notify_trade_closed(ts=_ts(minute=45), reason="TP")
    # During lockout: next 3 bars even with extreme z must not arm
    for i, (h, m) in enumerate([(14, 50), (14, 55), (15, 0)]):
        out = t.on_5m_close(ts=_ts(hour=h, minute=m), z=-2.8, beta=1.0, is_cointegrated=True)
        assert out is None, f"bar {i} inside lockout should return None"
    # Bar 4 (lockout expired) should arm again
    out = t.on_5m_close(ts=_ts(hour=15, minute=5), z=-2.8, beta=1.0, is_cointegrated=True)
    assert out is not None


def test_trading_day_reset_clears_armed_state():
    t = PairSpreadTracker()
    # Arm on day 1 at 14:30 UTC (09:30 ET)
    t.on_5m_close(ts=_ts(day=17, hour=14, minute=30), z=-2.5, beta=1.0, is_cointegrated=True)
    assert t.state == STATE_ARMED_LONG
    # Day 2 bar at 14:30 UTC next day → reset
    out = t.on_5m_close(ts=_ts(day=18, hour=14, minute=30), z=1.0, beta=1.0, is_cointegrated=True)
    assert out is None  # z below entry threshold, but state reset to IDLE
    assert t.state == STATE_IDLE


def test_nan_z_or_beta_yields_no_setup():
    import math
    t = PairSpreadTracker()
    out = t.on_5m_close(ts=_ts(), z=math.nan, beta=1.0, is_cointegrated=True)
    assert out is None
    out = t.on_5m_close(ts=_ts(), z=-2.5, beta=math.nan, is_cointegrated=True)
    assert out is None


def test_trace_records_transitions():
    t = PairSpreadTracker()
    t.on_5m_close(ts=_ts(minute=30), z=-2.5, beta=1.0, is_cointegrated=True)
    t.notify_trade_closed(ts=_ts(minute=45), reason="TP")
    trace = t.trace
    assert any(entry[0] == STATE_ARMED_LONG for entry in trace)
    assert any(entry[0] == "TRADE_CLOSED" for entry in trace)
