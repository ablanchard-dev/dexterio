"""Playbooks must age a sweep whatever the tz-awareness of the two clocks.

Seen live on 2026-09-17: the pipeline clock is `datetime.now(timezone.utc)`
(aware) while `LiquidityEngine` stamps sweeps with `datetime.utcnow()` (naive).
The subtraction raised TypeError inside the playbook checks and the whole
symbol (QQQ) was dropped from the pipeline, silently, on every cycle.
"""
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from engines import playbooks
from engines.playbooks import _seconds_since


def test_aware_now_vs_naive_sweep_is_the_live_case():
    now = datetime(2026, 9, 17, 14, 0, tzinfo=timezone.utc)
    sweep = datetime(2026, 9, 17, 13, 45)  # naive UTC, as LiquidityEngine stamps it
    assert _seconds_since(now, sweep) == pytest.approx(900)


def test_naive_now_vs_aware_sweep():
    now = datetime(2026, 9, 17, 14, 0)
    sweep = datetime(2026, 9, 17, 13, 30, tzinfo=timezone.utc)
    assert _seconds_since(now, sweep) == pytest.approx(1800)


def test_both_aware_in_different_zones_compare_on_the_instant():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone(timedelta(hours=2)))  # 14:00 UTC
    sweep = datetime(2026, 9, 17, 13, 50, tzinfo=timezone.utc)
    assert _seconds_since(now, sweep) == pytest.approx(600)


def test_both_naive_unchanged():
    now = datetime(2026, 9, 17, 14, 0)
    assert _seconds_since(now, now - timedelta(minutes=5)) == pytest.approx(300)


def test_no_playbook_subtracts_sweep_timestamps_directly():
    """Every sweep-age check goes through the helper, so the live mix cannot come back."""
    src = inspect.getsource(playbooks)
    assert "- s.sweep_timestamp" not in src
    assert src.count("_seconds_since(current_time, s.sweep_timestamp)") >= 3
