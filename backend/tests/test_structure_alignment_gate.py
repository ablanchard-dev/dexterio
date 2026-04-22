"""Option A v2 O2.4 — structure_alignment gate tests.

Two required cases per plan:
    1. Setup LONG + last k3 pivot = LOW  → accept (structure bullish).
    2. Setup LONG + last k3 pivot = HIGH → reject (funnel counter traced).

Also validates that the funnel counter increments with the expected keys so
O5.2 verdict item #9 can be populated without extra plumbing.
"""
from __future__ import annotations

from datetime import datetime

from engines.features.pivot import Pivot
from engines.setup_engine_v2 import SetupEngineV2


def _gate_harness() -> SetupEngineV2:
    # Construct the engine; the gate method is pure w.r.t. engine state
    # except for the instrumentation dict it owns.
    return SetupEngineV2()


def test_long_with_last_k3_pivot_low_accepts():
    engine = _gate_harness()
    pivots = {
        "k3": [
            Pivot(index=10, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 0)),
            Pivot(index=20, price=450.0, type="low", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    result = engine._apply_structure_alignment_gate(
        playbook_name="Aplus_03_v2",
        direction="LONG",
        align_tf="k3",
        structure_pivots=pivots,
    )
    assert result == "low"
    stats = engine._structure_gate_stats["Aplus_03_v2"]
    assert stats["evaluated"] == 1
    assert stats["pass_aligned"] == 1
    assert stats["rejected"] == 0
    assert stats["long_evaluated"] == 1


def test_long_with_last_k3_pivot_high_rejects():
    engine = _gate_harness()
    pivots = {
        "k3": [
            Pivot(index=10, price=450.0, type="low", timestamp=datetime(2025, 7, 15, 14, 0)),
            Pivot(index=20, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    result = engine._apply_structure_alignment_gate(
        playbook_name="Aplus_03_v2",
        direction="LONG",
        align_tf="k3",
        structure_pivots=pivots,
    )
    assert result is None
    stats = engine._structure_gate_stats["Aplus_03_v2"]
    assert stats["evaluated"] == 1
    assert stats["rejected"] == 1
    assert stats["reject_long_vs_bear"] == 1
    assert stats["pass_aligned"] == 0


def test_short_mirror_accepts_on_last_high():
    engine = _gate_harness()
    pivots = {
        "k3": [
            Pivot(index=20, price=455.0, type="high", timestamp=datetime(2025, 7, 15, 14, 20)),
        ],
    }
    result = engine._apply_structure_alignment_gate(
        playbook_name="Aplus_03_v2",
        direction="SHORT",
        align_tf="k3",
        structure_pivots=pivots,
    )
    assert result == "high"
    stats = engine._structure_gate_stats["Aplus_03_v2"]
    assert stats["pass_aligned"] == 1


def test_no_pivots_rejects_fail_closed():
    engine = _gate_harness()
    result = engine._apply_structure_alignment_gate(
        playbook_name="Aplus_03_v2",
        direction="LONG",
        align_tf="k3",
        structure_pivots={"k3": []},
    )
    assert result is None
    stats = engine._structure_gate_stats["Aplus_03_v2"]
    assert stats["rejected"] == 1
    assert stats["rejected_no_pivots_at_tf"] == 1


def test_none_cache_rejects_fail_closed_distinguishable():
    engine = _gate_harness()
    result = engine._apply_structure_alignment_gate(
        playbook_name="Aplus_03_v2",
        direction="LONG",
        align_tf="k3",
        structure_pivots=None,
    )
    assert result is None
    stats = engine._structure_gate_stats["Aplus_03_v2"]
    assert stats["rejected"] == 1
    assert stats["rejected_no_pivot_cache"] == 1
