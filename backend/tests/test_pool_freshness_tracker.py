"""Tests for §0.B.7 pool_freshness_tracker."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.features.pool_freshness_tracker import (
    ET,
    Pool,
    PoolFreshnessTracker,
    PoolKind,
    PoolTF,
    compute_trading_date,
)


def _ts(y: int, m: int, d: int, h: int = 9, mm: int = 30) -> datetime:
    return datetime(y, m, d, h, mm, tzinfo=ET)


def _pool(pid: str, tf: str, kind: str, price: float, ts: datetime) -> Pool:
    return Pool(id=pid, tf=tf, kind=kind, price=price, created_ts=ts)


def test_register_and_freshness_initial_state():
    """A newly-registered pool is fresh until swept."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    p = _pool("4h_high_1", PoolTF.H4.value, PoolKind.HIGH.value, 450.0, _ts(2025, 11, 17, 10, 0))
    tracker.register_pool(p)
    assert tracker.is_fresh("4h_high_1") is True
    assert tracker.is_fresh("nonexistent") is False
    assert len(tracker) == 1


def test_update_detects_sweep_high_pool():
    """HIGH pool is swept when a later bar's high exceeds the pool price strictly."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    created = _ts(2025, 11, 17, 10, 0)
    tracker.register_pool(_pool("4h_high", PoolTF.H4.value, PoolKind.HIGH.value, 450.0, created))

    # Bar before creation must not sweep.
    pre = tracker.update(_ts(2025, 11, 17, 9, 55), bar_high=451.0, bar_low=449.0)
    assert pre == []
    assert tracker.is_fresh("4h_high") is True

    # Bar at creation timestamp: also does not sweep (strict > creation).
    at = tracker.update(_ts(2025, 11, 17, 10, 0), bar_high=451.0, bar_low=449.0)
    assert at == []

    # Bar after creation with high > price → sweep.
    swept = tracker.update(_ts(2025, 11, 17, 10, 5), bar_high=450.50, bar_low=449.50)
    assert swept == ["4h_high"]
    assert tracker.is_fresh("4h_high") is False

    # Equality (bar_high == pool.price) at a later bar does NOT sweep (penetration strict).
    tracker.register_pool(_pool("equality_high", PoolTF.H4.value, PoolKind.HIGH.value, 460.0, created))
    swept2 = tracker.update(_ts(2025, 11, 17, 10, 10), bar_high=460.0, bar_low=459.0)
    assert "equality_high" not in swept2
    assert tracker.is_fresh("equality_high") is True


def test_update_detects_sweep_low_pool_and_short_mirror():
    """LOW pool (SSL) is swept when bar_low < pool.price. Direction_target mirrors."""
    tracker = PoolFreshnessTracker(symbol="QQQ")
    created = _ts(2025, 11, 17, 10, 0)
    low_pool = _pool("4h_low", PoolTF.H4.value, PoolKind.LOW.value, 390.0, created)
    tracker.register_pool(low_pool)

    assert low_pool.direction_target == "short_target"

    swept = tracker.update(_ts(2025, 11, 17, 10, 5), bar_high=391.5, bar_low=389.99)
    assert swept == ["4h_low"]
    assert tracker.is_fresh("4h_low") is False

    # Also check the HIGH direction_target.
    high_pool = _pool("prev_D_high", PoolTF.PREV_D.value, PoolKind.HIGH.value, 500.0, created)
    tracker.register_pool(high_pool)
    assert high_pool.direction_target == "long_target"


def test_get_fresh_pools_filters_and_tf_priority_ordering():
    """get_fresh_pools respects tf_filter, direction, as_of, and sorts by TF priority."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    base = _ts(2025, 11, 17, 10, 0)

    # Mix of TFs and kinds.
    tracker.register_pool(_pool("p_1h_h", PoolTF.H1.value, PoolKind.HIGH.value, 455.0, base))
    tracker.register_pool(_pool("p_4h_h", PoolTF.H4.value, PoolKind.HIGH.value, 460.0, base + timedelta(minutes=5)))
    tracker.register_pool(_pool("p_prevD_l", PoolTF.PREV_D.value, PoolKind.LOW.value, 440.0, base))
    tracker.register_pool(_pool("p_5m_h", PoolTF.M5.value, PoolKind.HIGH.value, 453.0, base))
    tracker.register_pool(_pool("p_prevW_h", PoolTF.PREV_W.value, PoolKind.HIGH.value, 470.0, base))

    # Filter TF: 4h + 1h, direction long_target. Expect 4h before 1h (priority).
    fresh = tracker.get_fresh_pools(tf_filter=["4h", "1h"], direction="long_target")
    assert [p.id for p in fresh] == ["p_4h_h", "p_1h_h"]

    # Direction only → all HIGH pools, ordered by TF priority (W→4h→D→1h→5m).
    fresh_long = tracker.get_fresh_pools(direction="long_target")
    assert [p.id for p in fresh_long] == ["p_prevW_h", "p_4h_h", "p_1h_h", "p_5m_h"]

    # as_of earlier than created → excluded.
    none_yet = tracker.get_fresh_pools(tf_filter=["4h"], as_of=base + timedelta(minutes=1))
    assert none_yet == []  # p_4h_h created at base+5min

    # Direction short_target → only LOW pools.
    fresh_short = tracker.get_fresh_pools(direction="short_target")
    assert [p.id for p in fresh_short] == ["p_prevD_l"]


def test_mark_swept_manual_and_is_unswept_since():
    """mark_swept sets swept_ts; is_unswept_since respects the boundary."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    created = _ts(2025, 11, 17, 9, 0)
    tracker.register_pool(_pool("p1", PoolTF.H4.value, PoolKind.HIGH.value, 450.0, created))

    # Initially fresh.
    assert tracker.is_fresh("p1") is True
    # is_unswept_since a future boundary: True (never swept).
    assert tracker.is_unswept_since("p1", _ts(2025, 11, 17, 12, 0)) is True

    # Mark swept manually.
    sweep_ts = _ts(2025, 11, 17, 10, 30)
    assert tracker.mark_swept("p1", sweep_ts) is True
    assert tracker.is_fresh("p1") is False

    # is_unswept_since: boundary BEFORE sweep → False (swept after boundary).
    assert tracker.is_unswept_since("p1", _ts(2025, 11, 17, 10, 0)) is False
    # boundary AFTER sweep → True (pool was unswept during the "since" window... no wait,
    # unswept_since means swept_ts < since_ts, i.e. sweep happened in the past before the boundary).
    assert tracker.is_unswept_since("p1", _ts(2025, 11, 17, 11, 0)) is True

    # Idempotency: earlier swept_ts overrides.
    earlier = _ts(2025, 11, 17, 10, 0)
    tracker.mark_swept("p1", earlier)
    assert tracker._pools["p1"].swept_ts == earlier

    # Nonexistent pool.
    assert tracker.mark_swept("ghost", sweep_ts) is False
    assert tracker.is_unswept_since("ghost", sweep_ts) is False


def test_trading_day_rollover_clears_session_scoped_only():
    """18:00 ET rollover wipes session-scoped TFs; daily/weekly/hourly persist."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    day1_ny = _ts(2025, 11, 17, 10, 0)
    tracker.register_pool(_pool("asia_h", PoolTF.ASIAN.value, PoolKind.HIGH.value, 450.0, day1_ny))
    tracker.register_pool(_pool("lon_l", PoolTF.LONDON.value, PoolKind.LOW.value, 440.0, day1_ny))
    tracker.register_pool(_pool("4h_h", PoolTF.H4.value, PoolKind.HIGH.value, 460.0, day1_ny))
    tracker.register_pool(_pool("prevD_l", PoolTF.PREV_D.value, PoolKind.LOW.value, 430.0, day1_ny))
    tracker.register_pool(_pool("1h_h", PoolTF.H1.value, PoolKind.HIGH.value, 455.0, day1_ny))

    # Prime trading_date with a bar on day1.
    tracker.update(day1_ny, bar_high=449.0, bar_low=448.0)
    assert len(tracker) == 5

    # Bar at 18:05 ET on day1 → belongs to the next trading day → rollover triggers.
    rollover_bar = _ts(2025, 11, 17, 18, 5)
    tracker.update(rollover_bar, bar_high=445.0, bar_low=444.0)

    remaining = set(tracker.snapshot().keys())
    assert "asia_h" not in remaining
    assert "lon_l" not in remaining
    assert remaining == {"4h_h", "prevD_l", "1h_h"}


def test_get_fresh_pools_excludes_swept_and_as_of_cutoff():
    """Swept pools disappear from get_fresh_pools; as_of excludes future-created pools."""
    tracker = PoolFreshnessTracker(symbol="SPY")
    t0 = _ts(2025, 11, 17, 9, 0)
    t1 = _ts(2025, 11, 17, 10, 0)
    t2 = _ts(2025, 11, 17, 11, 0)

    tracker.register_pool(_pool("old_h", PoolTF.H4.value, PoolKind.HIGH.value, 450.0, t0))
    tracker.register_pool(_pool("new_h", PoolTF.H4.value, PoolKind.HIGH.value, 460.0, t2))

    # Sweep old_h at t1.
    swept = tracker.update(t1, bar_high=451.0, bar_low=449.0)
    assert swept == ["old_h"]

    # Query as of t1 → only pools created ≤ t1 and unswept.
    fresh_at_t1 = tracker.get_fresh_pools(tf_filter=["4h"], as_of=t1)
    assert fresh_at_t1 == []  # old_h swept, new_h not yet created

    # Query as of t2 → new_h visible (old_h still swept).
    fresh_at_t2 = tracker.get_fresh_pools(tf_filter=["4h"], as_of=t2)
    assert [p.id for p in fresh_at_t2] == ["new_h"]


def test_picklable_persistence_across_restart():
    """Tracker state round-trips through pickle (paper/live continuity)."""
    import pickle

    tracker = PoolFreshnessTracker(symbol="SPY")
    created = _ts(2025, 11, 17, 10, 0)
    tracker.register_pool(_pool("p1", PoolTF.H4.value, PoolKind.HIGH.value, 450.0, created))
    tracker.update(_ts(2025, 11, 17, 10, 30), bar_high=451.0, bar_low=449.0)
    assert tracker.is_fresh("p1") is False

    data = pickle.dumps(tracker)
    restored = pickle.loads(data)

    assert isinstance(restored, PoolFreshnessTracker)
    assert restored.symbol == "SPY"
    assert restored.is_fresh("p1") is False
    p = restored.get_pool("p1")
    assert p is not None
    assert p.swept_ts is not None


def test_compute_trading_date_18_ET_rollover():
    """compute_trading_date: 18:00 ET is boundary."""
    before_rollover = _ts(2025, 11, 17, 17, 59)
    assert compute_trading_date(before_rollover) == before_rollover.date()

    at_rollover = _ts(2025, 11, 17, 18, 0)
    assert compute_trading_date(at_rollover) == at_rollover.date() + timedelta(days=1)

    after_rollover = _ts(2025, 11, 17, 23, 45)
    assert compute_trading_date(after_rollover) == after_rollover.date() + timedelta(days=1)

    # UTC-aware input (engine convention) — tz convert to ET.
    utc = ZoneInfo("UTC")
    late_utc = datetime(2025, 11, 17, 23, 30, tzinfo=utc)  # = 18:30 ET
    assert compute_trading_date(late_utc) == late_utc.astimezone(ET).date() + timedelta(days=1)
