"""Option A v2 O1.4 — tp_resolver liquidity_draw swing_k3.

Four required cases per plan:
    1. LONG + swing_k3 pool inside lookback → TP = pool price.
    2. LONG + no pool in lookback → TP = fallback_rr × sl_distance.
    3. SHORT + swing_k3 pool → mirror of (1).
    4. min_rr_floor binding: pool too close → TP = min_rr_floor × sl_distance,
       reason = "fallback_rr_min_floor_binding".
"""
from __future__ import annotations

from datetime import datetime

import pytest

from engines.execution.tp_resolver import resolve_tp_price
from engines.features.pivot import Pivot


def _make_bars(n: int) -> list:
    """Minimal bar shim — tp_resolver only reads `len(bars)` to bound the
    lookback window. OHLC isn't consulted in this path."""
    class _Bar:
        pass
    out = []
    for _ in range(n):
        b = _Bar()
        out.append(b)
    return out


def test_long_with_pool_in_lookback_returns_pool_price():
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=50, price=448.0, type="low", timestamp=datetime(2025, 7, 15, 14, 0)),
            Pivot(index=70, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,  # sl_dist = 1.0 → min_floor = 0.5, floor_price = 450.5
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 455.0
    assert reason == "liquidity_draw_swing_k3"


def test_long_no_pool_in_lookback_falls_back_to_rr():
    bars = _make_bars(100)
    pivots = {
        # Pivot at index 10 is outside the lookback (100-60=40 is the cutoff).
        "k3": [
            Pivot(index=10, price=460.0, type="high", timestamp=datetime(2025, 7, 15, 9, 30)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,  # sl_dist = 1.0
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 452.0  # 450 + 1 * 2.0
    assert reason == "fallback_rr_no_pool"


def test_short_with_pool_mirror_of_long():
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=60, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 10)),
            Pivot(index=80, price=445.0, type="low", timestamp=datetime(2025, 7, 15, 14, 30)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=451.0,  # sl_dist = 1.0 → floor_price = 449.5
        direction="SHORT",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 445.0
    assert reason == "liquidity_draw_swing_k3"


def test_min_rr_floor_binding_when_pool_too_close():
    bars = _make_bars(100)
    # Pool sits 0.2R above entry — under the 0.5R floor.
    pivots = {
        "k3": [
            Pivot(index=70, price=450.2, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k3", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,  # sl_dist = 1.0, floor = 450.5
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 450.5  # min_rr_floor binds
    assert reason == "fallback_rr_min_floor_binding"


def test_unknown_draw_type_raises():
    with pytest.raises(ValueError):
        resolve_tp_price(
            tp_logic="liquidity_draw",
            tp_logic_params={"draw_type": "vwap_band_upper"},
            tp1_rr=2.0,
            entry_price=450.0,
            sl_price=449.0,
            direction="LONG",
            bars=_make_bars(10),
            structure_pivots={"k3": []},
        )


# --- Option \u03b1'' (2026-04-22): pool_selection="significant" ----------------

def _params_significant(max_rr_ceiling: float, **overrides):
    base = {
        "draw_type": "swing_k3",
        "lookback_bars": 60,
        "min_rr_floor": 0.5,
        "fallback_rr": 2.0,
        "pool_selection": "significant",
        "max_rr_ceiling": max_rr_ceiling,
    }
    base.update(overrides)
    return base


def test_significant_long_picks_farthest_in_band():
    """3 high pivots: 0.3R (below floor), 1.2R (in band), 2.5R (in band).
    'significant' picks the FARTHEST in band = 2.5R, not 1.2R (legacy nearest)."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=50, price=450.3, type="high", timestamp=datetime(2025, 7, 15, 14, 0)),   # 0.3R
            Pivot(index=60, price=451.2, type="high", timestamp=datetime(2025, 7, 15, 14, 10)),  # 1.2R
            Pivot(index=70, price=452.5, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),  # 2.5R
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params=_params_significant(max_rr_ceiling=3.0),
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,  # sl_dist=1.0
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 452.5
    assert reason == "liquidity_draw_swing_k3"


def test_significant_long_all_pools_beyond_ceiling():
    """Pool at 5R, ceiling at 3R \u2192 fallback_rr_pool_beyond_ceiling (TP = 2R fallback)."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=70, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),  # 5R
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params=_params_significant(max_rr_ceiling=3.0),
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 452.0  # 450 + 1 * 2.0 (fallback_rr)
    assert reason == "fallback_rr_pool_beyond_ceiling"


def test_significant_short_mirror_picks_farthest_in_band():
    """SHORT: 3 low pivots 0.3R, 1.2R, 2.5R below entry \u2192 picks 2.5R (lowest price)."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=50, price=449.7, type="low", timestamp=datetime(2025, 7, 15, 14, 0)),   # 0.3R
            Pivot(index=60, price=448.8, type="low", timestamp=datetime(2025, 7, 15, 14, 10)),  # 1.2R
            Pivot(index=70, price=447.5, type="low", timestamp=datetime(2025, 7, 15, 14, 20)),  # 2.5R
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params=_params_significant(max_rr_ceiling=3.0),
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=451.0,  # sl_dist=1.0
        direction="SHORT",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 447.5
    assert reason == "liquidity_draw_swing_k3"


def test_significant_below_floor_precedence_over_beyond_ceiling():
    """1 pool below floor (0.2R), 1 above ceiling (5R). Floor takes precedence
    (nearby micro-pivot is more actionable info than a distant outlier)."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=50, price=450.2, type="high", timestamp=datetime(2025, 7, 15, 14, 0)),   # 0.2R
            Pivot(index=70, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),  # 5R
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params=_params_significant(max_rr_ceiling=3.0),
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 450.5  # floor binds
    assert reason == "fallback_rr_min_floor_binding"


def test_significant_requires_max_rr_ceiling():
    bars = _make_bars(100)
    pivots = {"k3": [Pivot(index=70, price=451.5, type="high", timestamp=datetime(2025, 7, 15, 14, 20))]}
    with pytest.raises(ValueError, match="max_rr_ceiling"):
        resolve_tp_price(
            tp_logic="liquidity_draw",
            tp_logic_params={
                "draw_type": "swing_k3",
                "lookback_bars": 60,
                "min_rr_floor": 0.5,
                "fallback_rr": 2.0,
                "pool_selection": "significant",
                # max_rr_ceiling missing on purpose.
            },
            tp1_rr=2.0,
            entry_price=450.0,
            sl_price=449.0,
            direction="LONG",
            bars=bars,
            structure_pivots=pivots,
        )


def test_unknown_pool_selection_raises():
    bars = _make_bars(100)
    with pytest.raises(ValueError, match="pool_selection"):
        resolve_tp_price(
            tp_logic="liquidity_draw",
            tp_logic_params={
                "draw_type": "swing_k3",
                "lookback_bars": 60,
                "min_rr_floor": 0.5,
                "fallback_rr": 2.0,
                "pool_selection": "magnetic",
            },
            tp1_rr=2.0,
            entry_price=450.0,
            sl_price=449.0,
            direction="LONG",
            bars=bars,
            structure_pivots={"k3": []},
        )


# --- Option \u03b4 (2026-04-22): draw_type="swing_k9" ---------------------------

def test_swing_k9_reads_k9_pivots_not_k3():
    """draw_type=swing_k9 must look at structure_pivots['k9'], not k3.
    If k3 has a pool but k9 is empty -> no_pool."""
    bars = _make_bars(100)
    pivots = {
        "k3": [Pivot(index=70, price=451.5, type="high", timestamp=datetime(2025, 7, 15, 14, 20))],
        "k9": [],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k9", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 452.0  # 450 + 1 * 2.0 (fallback_rr)
    assert reason == "fallback_rr_no_pool"


def test_swing_k9_pool_hit_emits_k9_reason():
    """swing_k9 finds a pool -> reason must be 'liquidity_draw_swing_k9'."""
    bars = _make_bars(100)
    pivots = {
        "k3": [],
        "k9": [Pivot(index=70, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20))],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={"draw_type": "swing_k9", "lookback_bars": 60, "min_rr_floor": 0.5, "fallback_rr": 2.0},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 455.0
    assert reason == "liquidity_draw_swing_k9"


def test_swing_k9_significant_mode_short():
    """swing_k9 + significant mode on SHORT picks farthest k9 low in band."""
    bars = _make_bars(100)
    pivots = {
        "k3": [Pivot(index=60, price=449.0, type="low", timestamp=datetime(2025, 7, 15, 14, 10))],  # ignored
        "k9": [
            Pivot(index=50, price=449.7, type="low", timestamp=datetime(2025, 7, 15, 14, 0)),   # 0.3R (below floor)
            Pivot(index=65, price=448.5, type="low", timestamp=datetime(2025, 7, 15, 14, 15)),  # 1.5R (in band)
            Pivot(index=75, price=447.0, type="low", timestamp=datetime(2025, 7, 15, 14, 25)),  # 3.0R (at ceiling edge)
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k9",
            "lookback_bars": 60,
            "min_rr_floor": 0.5,
            "fallback_rr": 2.0,
            "pool_selection": "significant",
            "max_rr_ceiling": 3.0,
        },
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=451.0,  # sl_dist=1.0
        direction="SHORT",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 447.0  # farthest in-band k9 pivot
    assert reason == "liquidity_draw_swing_k9"


def test_nearest_mode_preserves_legacy_behavior():
    """Same fixture as test_significant_long_picks_farthest_in_band but
    pool_selection='nearest' \u2192 picks NEAREST (1.2R, NOT 2.5R)."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=50, price=450.3, type="high", timestamp=datetime(2025, 7, 15, 14, 0)),
            Pivot(index=60, price=451.2, type="high", timestamp=datetime(2025, 7, 15, 14, 10)),
            Pivot(index=70, price=452.5, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    # The 0.3R pool is closest, but it's below floor 0.5 \u2192 floor binds.
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "lookback_bars": 60,
            "min_rr_floor": 0.5,
            "fallback_rr": 2.0,
            # pool_selection unset \u2192 default "nearest"
        },
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 450.5
    assert reason == "fallback_rr_min_floor_binding"


# ---------------------------------------------------------------------------
# Option ε (2026-04-22) — reject_on_fallback
# ---------------------------------------------------------------------------


def test_reject_on_fallback_no_pool_emits_reject_prefix():
    """Option ε: when no pool in the direction and reject_on_fallback=True,
    resolver returns a 'reject_' prefix so setup_engine_v2 drops the setup.
    tp_price is a sentinel (legacy fallback_rr), never consumed by the caller."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=10, price=460.0, type="high", timestamp=datetime(2025, 7, 15, 9, 30)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "lookback_bars": 60,
            "min_rr_floor": 0.5,
            "fallback_rr": 2.0,
            "pool_selection": "significant",
            "max_rr_ceiling": 3.0,
            "reject_on_fallback": True,
        },
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert reason.startswith("reject_")
    assert reason == "reject_on_fallback_no_pool"
    assert tp == 452.0  # sentinel (fallback_rr × sl_dist), never read by caller


def test_reject_on_fallback_pool_in_band_still_returns_pool():
    """Option ε: when a pool IS in the band, reject_on_fallback=True is a no-op —
    the setup proceeds with the normal liquidity_draw TP."""
    bars = _make_bars(100)
    pivots = {
        "k3": [
            Pivot(index=60, price=452.5, type="high", timestamp=datetime(2025, 7, 15, 14, 10)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "lookback_bars": 60,
            "min_rr_floor": 0.5,
            "fallback_rr": 2.0,
            "pool_selection": "significant",
            "max_rr_ceiling": 3.0,
            "reject_on_fallback": True,
        },
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert tp == 452.5
    assert reason == "liquidity_draw_swing_k3"


def test_reject_on_fallback_default_false_preserves_legacy_fallback():
    """Option ε back-compat: without the flag, no_pool still returns the
    legacy fallback_rr_no_pool reason (not reject_)."""
    bars = _make_bars(100)
    pivots = {"k3": []}
    tp, reason = resolve_tp_price(
        tp_logic="liquidity_draw",
        tp_logic_params={
            "draw_type": "swing_k3",
            "lookback_bars": 60,
            "min_rr_floor": 0.5,
            "fallback_rr": 2.0,
        },
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=449.0,
        direction="LONG",
        bars=bars,
        structure_pivots=pivots,
    )
    assert reason == "fallback_rr_no_pool"
    assert not reason.startswith("reject_")
    assert tp == 452.0
