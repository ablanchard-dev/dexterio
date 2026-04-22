"""Unit tests for Aplus01Tracker — Family A sequential state machine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from engines.features.aplus01_tracker import (
    STATE_ARMED,
    STATE_BOS,
    STATE_IDLE,
    STATE_TOUCHED,
    Aplus01Tracker,
)


@dataclass
class B:
    open: float
    high: float
    low: float
    close: float


def _ts(year=2025, month=11, day=17, hour=14, minute=30, second=0) -> datetime:
    # 14:30 UTC = 09:30 ET (EST) — NY session open in November.
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _flat_1m(n: int, base: float = 100.0) -> list[B]:
    return [B(base, base + 0.05, base - 0.05, base) for _ in range(n)]


# --------------------------------------------------------------------------
# 1. State transitions
# --------------------------------------------------------------------------

def test_idle_stays_idle_without_sweep():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(), sweep=None, bos=None, zones=[])
    assert tr.get_state("SPY") == STATE_IDLE


def test_sweep_bullish_arms_bearish():
    tr = Aplus01Tracker()
    tr.on_5m_close(
        "SPY", _ts(),
        sweep={"direction": "bullish", "extreme_price": 101.25},
    )
    assert tr.get_state("SPY") == STATE_ARMED


def test_sweep_bearish_arms_bullish():
    tr = Aplus01Tracker()
    tr.on_5m_close(
        "SPY", _ts(),
        sweep={"direction": "bearish", "extreme_price": 98.75},
    )
    assert tr.get_state("SPY") == STATE_ARMED


def test_armed_bos_counter_direction_advances():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bearish"})
    assert tr.get_state("SPY") == STATE_BOS


def test_armed_bos_same_direction_rejected():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    # armed_direction=bearish; a "bullish" BOS does NOT advance.
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bullish"})
    assert tr.get_state("SPY") == STATE_ARMED


def test_bos_to_confluence_touched_on_zone_overlap():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bearish"})
    zones = [{"type": "fvg", "low": 100.4, "high": 100.8, "id": "fvg-1"}]
    tr.on_5m_close(
        "SPY", _ts(minute=40),
        zones=zones, bar_high=100.6, bar_low=100.3,
    )
    assert tr.get_state("SPY") == STATE_TOUCHED


# --------------------------------------------------------------------------
# 2. Timeouts
# --------------------------------------------------------------------------

def test_sweep_timeout_resets_to_idle():
    tr = Aplus01Tracker(sweep_timeout=3)
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    # 4 more 5m bars without BOS → exceeds sweep_timeout=3.
    for i in range(1, 5):
        tr.on_5m_close("SPY", _ts(minute=30 + 5 * i))
    assert tr.get_state("SPY") == STATE_IDLE


def test_bos_timeout_resets_to_idle():
    tr = Aplus01Tracker(bos_timeout=2)
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bearish"})
    # 3 more 5m bars with no touch → exceeds bos_timeout=2.
    for i in range(2, 5):
        tr.on_5m_close("SPY", _ts(minute=30 + 5 * i))
    assert tr.get_state("SPY") == STATE_IDLE


def test_confirm_timeout_resets_to_idle():
    tr = Aplus01Tracker(confirm_timeout=3)
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bearish"})
    zones = [{"type": "fvg", "low": 100.4, "high": 100.8, "id": "z"}]
    tr.on_5m_close("SPY", _ts(minute=40),
                   zones=zones, bar_high=100.6, bar_low=100.3)
    # 4 flat 1m bars (no pressure) → exceed confirm_timeout=3.
    bars = _flat_1m(4)
    for i, b in enumerate(bars):
        tr.on_1m_bar("SPY", _ts(minute=40, second=i), b, bars[: i + 1])
    assert tr.get_state("SPY") == STATE_IDLE


# --------------------------------------------------------------------------
# 3. Emission + reset after emit
# --------------------------------------------------------------------------

def _arm_to_touched(tr: Aplus01Tracker, symbol: str = "SPY"):
    tr.on_5m_close(symbol, _ts(),
                   sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close(symbol, _ts(minute=35), bos={"direction": "bearish"})
    zones = [{"type": "fvg", "low": 100.4, "high": 100.8, "id": "z"}]
    tr.on_5m_close(symbol, _ts(minute=40),
                   zones=zones, bar_high=100.6, bar_low=100.3)


def test_emit_on_1m_pressure_returns_dict_and_resets():
    tr = Aplus01Tracker()
    _arm_to_touched(tr)
    assert tr.get_state("SPY") == STATE_TOUCHED

    # Build 1m pressure: flat bars then bearish BOS break (armed_direction=bearish).
    flat = _flat_1m(5)
    cur = B(100.0, 100.05, 99.4, 99.5)  # breaks below flat[-5:] low 99.95
    bars_1m = flat + [cur]

    emit = tr.on_1m_bar("SPY", _ts(minute=41), cur, bars_1m)
    assert emit is not None
    assert emit["direction"] == "bearish"
    assert emit["entry_price"] == pytest.approx(99.5)
    assert emit["sl_anchor_price"] == pytest.approx(101.0)
    assert emit["touched_zone_type"] == "fvg"
    assert emit["touched_zone_id"] == "z"
    assert emit["confirmed_at_ts"] is not None
    assert emit["armed_at_ts"] is not None
    assert emit["bos_at_ts"] is not None
    assert emit["touched_at_ts"] is not None
    assert ("EMIT", emit["confirmed_at_ts"], None) in emit["state_machine_trace"]
    # Single-shot: after emit, back to IDLE.
    assert tr.get_state("SPY") == STATE_IDLE


def test_no_emit_without_pressure():
    tr = Aplus01Tracker()
    _arm_to_touched(tr)
    flat = _flat_1m(3)
    emit = tr.on_1m_bar("SPY", _ts(minute=41), flat[-1], flat)
    assert emit is None
    assert tr.get_state("SPY") == STATE_TOUCHED


# --------------------------------------------------------------------------
# 4. Multi-symbol isolation
# --------------------------------------------------------------------------

def test_multi_symbol_state_isolation():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(),
                   sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("QQQ", _ts(),
                   sweep={"direction": "bearish", "extreme_price": 398.0})
    assert tr.get_state("SPY") == STATE_ARMED
    assert tr.get_state("QQQ") == STATE_ARMED

    # Advance SPY further; QQQ stays ARMED.
    tr.on_5m_close("SPY", _ts(minute=35), bos={"direction": "bearish"})
    assert tr.get_state("SPY") == STATE_BOS
    assert tr.get_state("QQQ") == STATE_ARMED


# --------------------------------------------------------------------------
# 5. Trading-date reset (18:00 ET rollover)
# --------------------------------------------------------------------------

def test_trading_date_reset_clears_state():
    tr = Aplus01Tracker()
    # Day 1, 14:30 UTC = 09:30 ET.
    tr.on_5m_close(
        "SPY", datetime(2025, 11, 17, 14, 30, tzinfo=timezone.utc),
        sweep={"direction": "bullish", "extreme_price": 101.0},
    )
    assert tr.get_state("SPY") == STATE_ARMED

    # Next day 00:00 UTC = 19:00 prev-day ET — new trading date (past 18:00 ET rollover).
    # Next 5m close on day 2 at 14:30 UTC should reset because trading_date changed.
    tr.on_5m_close("SPY", datetime(2025, 11, 18, 14, 30, tzinfo=timezone.utc))
    assert tr.get_state("SPY") == STATE_IDLE


# --------------------------------------------------------------------------
# 6. Edge cases
# --------------------------------------------------------------------------

def test_on_1m_bar_before_touched_returns_none():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(),
                   sweep={"direction": "bullish", "extreme_price": 101.0})
    # State = ARMED (not TOUCHED) — 1m calls must be inert.
    flat = _flat_1m(5)
    cur = B(100.0, 100.05, 99.4, 99.5)
    bars = flat + [cur]
    emit = tr.on_1m_bar("SPY", _ts(minute=35), cur, bars)
    assert emit is None
    assert tr.get_state("SPY") == STATE_ARMED


def test_reset_clears_all_symbols():
    tr = Aplus01Tracker()
    tr.on_5m_close("SPY", _ts(), sweep={"direction": "bullish", "extreme_price": 101.0})
    tr.on_5m_close("QQQ", _ts(), sweep={"direction": "bearish", "extreme_price": 398.0})
    tr.reset()
    assert tr.get_state("SPY") == STATE_IDLE
    assert tr.get_state("QQQ") == STATE_IDLE


def test_unknown_symbol_state_is_idle():
    tr = Aplus01Tracker()
    assert tr.get_state("NVDA") == STATE_IDLE


def test_naive_timestamp_treated_as_utc():
    tr = Aplus01Tracker()
    naive = datetime(2025, 11, 17, 14, 30)  # no tzinfo
    tr.on_5m_close("SPY", naive, sweep={"direction": "bullish", "extreme_price": 101.0})
    assert tr.get_state("SPY") == STATE_ARMED
