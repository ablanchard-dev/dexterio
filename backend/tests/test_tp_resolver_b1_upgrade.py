"""Tests for §0.B.1 tp_resolver upgrade (freshness + smt_completion + TF hierarchy).

Legacy behavior (structure_pivots only) is covered by existing tp_resolver tests.
These tests exercise the §0.B.1 additions:
  1. tp_logic="smt_completion" with valid smt_completion_price
  2. smt_completion missing price → fallback_rr_no_smt_completion
  3. smt_completion wrong side (behind entry) → fallback
  4. smt_completion reject_on_fallback → reject_on_fallback_no_smt_completion
  5. fresh_pools liquidity_draw "nearest" — TF priority 4h > 1h
  6. fresh_pools liquidity_draw "significant" — farthest in band
  7. fresh_pools tf_filter excludes disallowed TFs
  8. fresh_pools empty/wrong-direction → fallback to structure_pivots (legacy)
  9. fresh_pools below_floor / beyond_ceiling verdicts
 10. Backward-compat: resolver called without fresh_pools behaves exactly as pre-§0.B.1
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.execution.tp_resolver import resolve_tp_price
from engines.features.pivot import Pivot, PivotType
from engines.features.pool_freshness_tracker import Pool, PoolKind, PoolTF

ET = ZoneInfo("America/New_York")


def _ts(h: int = 10, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def _bars(n: int):
    """Minimal bars list — only `len(bars)` is read by resolver (for lookback_bars)."""
    class B:
        pass
    return [B() for _ in range(n)]


def _pool(tf: str, kind: str, price: float) -> Pool:
    return Pool(
        id=f"{tf}_{kind}_{price}",
        tf=tf,
        kind=kind,
        price=price,
        created_ts=_ts(9, 0),
    )


# --- 1. smt_completion valid ---

def test_smt_completion_long_returns_attached_swing_price():
    tp, reason = resolve_tp_price(
        tp_logic="smt_completion",
        tp_logic_params={"smt_completion_price": 452.30, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=_bars(100),
    )
    assert tp == pytest.approx(452.30)
    assert reason == "smt_completion"


def test_smt_completion_short_mirror():
    tp, reason = resolve_tp_price(
        tp_logic="smt_completion",
        tp_logic_params={"smt_completion_price": 397.50},
        tp1_rr=2.0,
        entry_price=400.0,
        sl_price=401.0,
        direction="SHORT",
        bars=_bars(50),
    )
    assert tp == pytest.approx(397.50)
    assert reason == "smt_completion"


# --- 2. smt_completion missing price ---

def test_smt_completion_missing_price_falls_back_to_rr():
    tp, reason = resolve_tp_price(
        tp_logic="smt_completion",
        tp_logic_params={"fallback_rr": 2.5},  # no smt_completion_price
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(10),
    )
    assert tp == pytest.approx(100.0 + 1.0 * 2.5)  # entry + sl_dist × fallback_rr
    assert reason == "fallback_rr_no_smt_completion"


# --- 3. smt_completion wrong side (behind entry) ---

def test_smt_completion_wrong_side_long_falls_back():
    # LONG trade but smt_price is BELOW entry (wrong side).
    tp, reason = resolve_tp_price(
        tp_logic="smt_completion",
        tp_logic_params={"smt_completion_price": 98.0},
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(10),
    )
    assert reason == "fallback_rr_no_smt_completion"
    assert tp == pytest.approx(100.0 + 1.0 * 2.0)  # default fallback_rr


# --- 4. smt_completion reject_on_fallback ---

def test_smt_completion_reject_on_fallback_emits_reject_reason():
    tp, reason = resolve_tp_price(
        tp_logic="smt_completion",
        tp_logic_params={"reject_on_fallback": True},  # no smt_price
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(10),
    )
    assert reason == "reject_on_fallback_no_smt_completion"
    # tp is a sentinel; caller (setup_engine_v2) checks the "reject_" prefix.


# --- 5. fresh_pools liquidity_draw "nearest" with TF priority ---

def test_fresh_pools_nearest_prefers_higher_tf_priority_on_tie():
    # Two pools at same distance; 4h should be picked over 5m (TF priority).
    pools = [
        _pool(PoolTF.M5.value, PoolKind.HIGH.value, 102.0),
        _pool(PoolTF.H4.value, PoolKind.HIGH.value, 102.0),  # same price
    ]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "pool_selection": "nearest",
            "min_rr_floor": 0.5,
        },
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(100),
        fresh_pools=pools,
    )
    # Both at 102.0, 4h wins on TF priority tiebreak.
    assert tp == pytest.approx(102.0)
    assert reason == "liquidity_draw_pool_4h"


def test_fresh_pools_nearest_picks_closest_to_entry():
    # Three pools at different distances; nearest wins.
    pools = [
        _pool(PoolTF.H4.value, PoolKind.HIGH.value, 110.0),  # far
        _pool(PoolTF.H1.value, PoolKind.HIGH.value, 103.0),  # close
        _pool(PoolTF.M15.value, PoolKind.HIGH.value, 105.0),  # mid
    ]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "pool_selection": "nearest"},
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(50),
        fresh_pools=pools,
    )
    assert tp == pytest.approx(103.0)
    assert reason == "liquidity_draw_pool_1h"


# --- 6. fresh_pools liquidity_draw "significant" — farthest in band ---

def test_fresh_pools_significant_picks_farthest_in_band():
    # Band [min_rr=0.5 → 0.5; max_rr=3.0 → 3.0] over sl_dist=1.0
    # → band = [100.5, 103.0] for LONG entry 100.
    pools = [
        _pool(PoolTF.H4.value, PoolKind.HIGH.value, 100.3),  # below floor
        _pool(PoolTF.H1.value, PoolKind.HIGH.value, 101.5),  # in band, near
        _pool(PoolTF.M15.value, PoolKind.HIGH.value, 102.8),  # in band, far → winner
        _pool(PoolTF.PREV_D.value, PoolKind.HIGH.value, 110.0),  # beyond ceiling
    ]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "pool_selection": "significant",
            "min_rr_floor": 0.5,
            "max_rr_ceiling": 3.0,
        },
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(50),
        fresh_pools=pools,
    )
    assert tp == pytest.approx(102.8)
    assert reason == "liquidity_draw_pool_15m"


# --- 7. fresh_pools tf_filter excludes disallowed TFs ---

def test_fresh_pools_tf_filter_only_keeps_allowed_tfs():
    pools = [
        _pool(PoolTF.M5.value, PoolKind.HIGH.value, 100.5),  # disallowed
        _pool(PoolTF.H4.value, PoolKind.HIGH.value, 103.0),  # allowed
    ]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "pool_selection": "nearest",
            "pool_tf": ["4h", "1h"],  # excludes 5m
        },
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(50),
        fresh_pools=pools,
    )
    assert tp == pytest.approx(103.0)
    assert reason == "liquidity_draw_pool_4h"


# --- 8. fresh_pools empty/wrong-dir → fallback to structure_pivots ---

def test_fresh_pools_empty_falls_back_to_structure_pivots():
    # Empty fresh_pools should fall through to structure_pivots (legacy).
    k3_pivot = Pivot(type="high", index=50, price=102.5, timestamp=_ts())
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "pool_selection": "nearest"},
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(100),
        structure_pivots={"k3": [k3_pivot]},
        fresh_pools=[],  # empty
    )
    assert tp == pytest.approx(102.5)
    assert reason == "liquidity_draw_swing_k3"  # legacy reason


def test_fresh_pools_all_wrong_direction_falls_back_to_structure_pivots():
    # Pools exist but all on wrong side → no_pool verdict → fallback.
    pools = [
        _pool(PoolTF.H4.value, PoolKind.LOW.value, 98.0),  # LOW pool on LONG trade → wrong dir
    ]
    k3_pivot = Pivot(type="high", index=50, price=102.0, timestamp=_ts())
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "pool_selection": "nearest"},
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(100),
        structure_pivots={"k3": [k3_pivot]},
        fresh_pools=pools,
    )
    assert reason == "liquidity_draw_swing_k3"  # legacy fallback


# --- 9. fresh_pools below_floor / beyond_ceiling ---

def test_fresh_pools_nearest_below_floor_returns_floor_price():
    # LONG, entry=100, sl=99 → sl_dist=1. floor rr=0.5 → floor_price=100.5.
    # Only pool is at 100.3 (below floor).
    pools = [_pool(PoolTF.H4.value, PoolKind.HIGH.value, 100.3)]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "pool_selection": "nearest",
            "min_rr_floor": 0.5,
        },
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(50),
        fresh_pools=pools,
    )
    assert tp == pytest.approx(100.5)  # floor
    assert reason == "fallback_rr_min_floor_binding"


def test_fresh_pools_significant_beyond_ceiling_returns_fallback_rr():
    # All pools are above the ceiling → beyond_ceiling verdict.
    pools = [
        _pool(PoolTF.H4.value, PoolKind.HIGH.value, 110.0),  # R=10.0 >> ceiling 3.0
    ]
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "pool_selection": "significant",
            "min_rr_floor": 0.5,
            "max_rr_ceiling": 3.0,
            "fallback_rr": 2.0,
        },
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(50),
        fresh_pools=pools,
    )
    assert tp == pytest.approx(102.0)  # fallback_rr applied
    assert reason == "fallback_rr_pool_beyond_ceiling"


# --- 10. Backward-compat: no fresh_pools arg keeps legacy signature ---

def test_backward_compat_no_fresh_pools_keeps_legacy_behavior():
    """Calling without fresh_pools produces byte-identical results to pre-§0.B.1."""
    k3_pivot = Pivot(type="high", index=50, price=103.0, timestamp=_ts())
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "pool_selection": "nearest"},
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(100),
        structure_pivots={"k3": [k3_pivot]},
        # fresh_pools omitted entirely
    )
    assert tp == pytest.approx(103.0)
    assert reason == "liquidity_draw_swing_k3"


def test_backward_compat_fixed_rr_unchanged():
    """tp_logic=fixed_rr still works identically (no §0.B.1 impact)."""
    tp, reason = resolve_tp_price(
        tp_logic="fixed_rr",
        tp_logic_params=None,
        tp1_rr=2.0,
        entry_price=100.0,
        sl_price=99.0,
        direction="LONG",
        bars=_bars(10),
    )
    assert tp == pytest.approx(102.0)
    assert reason == "fixed_rr"
