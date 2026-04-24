"""Tests for §0.B.8 fvg_stacking + pre-sweep gate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.patterns.fvg_stacking import (
    FVGCandle,
    check_pre_sweep_gate,
    group_fvg_stack,
    invalidate_stacked_fvgs,
)

ET = ZoneInfo("America/New_York")


def _ts(h: int, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


@dataclass
class Bar:
    open: float
    close: float
    timestamp: datetime


def _fvg(id_: str, lo: float, hi: float, direction: str, ts: datetime) -> FVGCandle:
    return FVGCandle(id=id_, low=lo, high=hi, direction=direction, created_ts=ts)


# --- group_fvg_stack ---

def test_stack_groups_consecutive_same_direction_bullish_fvgs():
    fvgs = [
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),
        _fvg("f2", 101.5, 102.5, "bullish", _ts(10, 10)),
        _fvg("f3", 103.0, 104.0, "bullish", _ts(10, 20)),
    ]
    # All green bars between → no opposite, same direction → single stack.
    bars = [
        Bar(open=100.0, close=101.0, timestamp=_ts(10, 5)),
        Bar(open=101.5, close=102.5, timestamp=_ts(10, 15)),
    ]
    stacks = group_fvg_stack(fvgs, bars)
    assert len(stacks) == 1
    assert [f.id for f in stacks[0]] == ["f1", "f2", "f3"]


def test_opposite_color_bar_breaks_stack():
    fvgs = [
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),
        _fvg("f2", 102.0, 103.0, "bullish", _ts(10, 20)),
    ]
    # A red bar (close < open) between → breaks the stack.
    bars = [
        Bar(open=101.0, close=100.5, timestamp=_ts(10, 10)),  # red → opposite to bullish
    ]
    stacks = group_fvg_stack(fvgs, bars)
    assert len(stacks) == 2
    assert [f.id for f in stacks[0]] == ["f1"]
    assert [f.id for f in stacks[1]] == ["f2"]


def test_mixed_direction_creates_separate_stacks():
    fvgs = [
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),
        _fvg("f2", 102.0, 103.0, "bearish", _ts(10, 10)),
        _fvg("f3", 99.0, 100.0, "bullish", _ts(10, 20)),
    ]
    stacks = group_fvg_stack(fvgs, [])
    assert len(stacks) == 3
    assert [[f.id for f in s] for s in stacks] == [["f1"], ["f2"], ["f3"]]


def test_empty_fvgs_returns_empty_list():
    assert group_fvg_stack([], []) == []


def test_stack_sorts_input_fvgs_defensively():
    # Provide FVGs out of order — stacker should sort by created_ts.
    fvgs = [
        _fvg("f2", 101.0, 102.0, "bullish", _ts(10, 10)),  # later
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),  # earlier
    ]
    stacks = group_fvg_stack(fvgs, [])
    assert [f.id for f in stacks[0]] == ["f1", "f2"]


# --- invalidate_stacked_fvgs ---

def test_last_invalidates_not_first_on_bullish_stack():
    """Bar closes through the last (highest) FVG → only the last is invalidated."""
    stack = [
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),
        _fvg("f2", 102.0, 103.0, "bullish", _ts(10, 10)),
        _fvg("f3", 104.0, 105.0, "bullish", _ts(10, 20)),  # last
    ]
    # Closing bar closes below f3.low (104) → invalidates f3 only.
    updated = invalidate_stacked_fvgs(
        stack, closing_bar_high=104.5, closing_bar_low=103.5, closing_bar_close=103.8
    )
    assert len(updated) == 3
    assert updated[0].invalidated is False  # f1 survives
    assert updated[1].invalidated is False  # f2 survives
    assert updated[2].invalidated is True  # f3 invalidated


def test_bearish_stack_last_invalidates_on_close_above():
    stack = [
        _fvg("b1", 100.0, 101.0, "bearish", _ts(10, 0)),
        _fvg("b2", 98.0, 99.0, "bearish", _ts(10, 10)),  # last (lower)
    ]
    # Closing bar closes above b2.high (99) → invalidates b2.
    updated = invalidate_stacked_fvgs(
        stack, closing_bar_high=99.5, closing_bar_low=98.5, closing_bar_close=99.3
    )
    assert updated[0].invalidated is False
    assert updated[1].invalidated is True


def test_no_invalidation_when_bar_doesnt_close_through_last_fvg():
    stack = [
        _fvg("f1", 100.0, 101.0, "bullish", _ts(10, 0)),
        _fvg("f2", 102.0, 103.0, "bullish", _ts(10, 10)),
    ]
    # Bar wicks into f2 but closes above f2.low → no invalidation.
    updated = invalidate_stacked_fvgs(
        stack, closing_bar_high=102.5, closing_bar_low=101.8, closing_bar_close=102.3
    )
    assert all(f.invalidated is False for f in updated)


def test_empty_stack_returns_empty():
    assert invalidate_stacked_fvgs([], 0.0, 0.0, 0.0) == []


# --- check_pre_sweep_gate ---

def test_pre_sweep_gate_within_window_returns_true():
    # Sweep at 10:00, current at 10:15, window 30 min → within (9:45, 10:15]
    assert check_pre_sweep_gate(
        sweep_event_ts=_ts(10, 0),
        current_ts=_ts(10, 15),
        max_window_minutes=30,
    ) is True


def test_pre_sweep_gate_outside_window_returns_false():
    # Sweep at 9:30, current at 10:15, window 30 min → 9:30 < 9:45 → outside.
    assert check_pre_sweep_gate(
        sweep_event_ts=_ts(9, 30),
        current_ts=_ts(10, 15),
        max_window_minutes=30,
    ) is False


def test_pre_sweep_gate_no_sweep_returns_false():
    assert check_pre_sweep_gate(
        sweep_event_ts=None,
        current_ts=_ts(10, 15),
        max_window_minutes=30,
    ) is False


def test_pre_sweep_gate_future_sweep_returns_false():
    # Sweep at 11:00 but current is 10:15 → future → invalid.
    assert check_pre_sweep_gate(
        sweep_event_ts=_ts(11, 0),
        current_ts=_ts(10, 15),
        max_window_minutes=30,
    ) is False


def test_pre_sweep_gate_zero_window_returns_false():
    assert check_pre_sweep_gate(
        sweep_event_ts=_ts(10, 0),
        current_ts=_ts(10, 15),
        max_window_minutes=0,
    ) is False
