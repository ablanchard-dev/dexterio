"""Tests for §0.B.5 macro kill zone overlay — entry_gates.check_macro_kill_zone."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.execution.entry_gates import (
    GATE_REASON_MANIPULATION_WINDOW,
    GATE_REASON_OUTSIDE_MACRO_WINDOW,
    GATE_REASON_POST_CUTOFF,
    check_macro_kill_zone,
)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def _et(h: int, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def test_macro_am_zone_allows_entry():
    """Bar at 09:55 ET → inside AM zone → pass."""
    result = check_macro_kill_zone(_et(9, 55), macro_am=True, macro_pm=True)
    assert result.passed is True
    assert result.reason is None


def test_macro_pm_zone_allows_entry():
    """Bar at 14:00 ET → inside PM zone → pass."""
    result = check_macro_kill_zone(_et(14, 0), macro_am=True, macro_pm=True)
    assert result.passed is True


def test_outside_both_windows_rejected():
    """Bar at 11:00 ET → outside AM (ended 10:10) and PM (starts 13:50) → reject."""
    result = check_macro_kill_zone(_et(11, 0), macro_am=True, macro_pm=True)
    assert result.passed is False
    assert result.reason == GATE_REASON_OUTSIDE_MACRO_WINDOW


def test_dst_transition_ny_utc_conversion():
    """UTC-aware timestamp converts correctly to ET across DST boundary."""
    # 2025-11-17 is post-DST (EST = UTC-5). 14:55 UTC = 09:55 EST → in AM zone.
    utc_ts = datetime(2025, 11, 17, 14, 55, tzinfo=UTC)
    result = check_macro_kill_zone(utc_ts, macro_am=True, macro_pm=True)
    assert result.passed is True


def test_strict_manip_gate_rejects_manipulation_window():
    """Strict mode: 09:35 ET (manipulation window) → reject."""
    result = check_macro_kill_zone(
        _et(9, 35), macro_am=True, macro_pm=True, strict_manip_gate=True
    )
    assert result.passed is False
    assert result.reason == GATE_REASON_MANIPULATION_WINDOW


def test_strict_manip_gate_rejects_post_cutoff():
    """Strict mode: 11:00 ET (post 10:30 cutoff, pre PM) → reject post_cutoff."""
    result = check_macro_kill_zone(
        _et(11, 0), macro_am=True, macro_pm=True, strict_manip_gate=True
    )
    assert result.passed is False
    assert result.reason == GATE_REASON_POST_CUTOFF


def test_both_disabled_is_noop_pass():
    """With both macro_am and macro_pm disabled, gate is a no-op pass."""
    result = check_macro_kill_zone(
        _et(23, 0), macro_am=False, macro_pm=False
    )
    assert result.passed is True
    assert result.reason is None
