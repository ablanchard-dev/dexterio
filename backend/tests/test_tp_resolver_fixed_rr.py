"""Option A v2 O1.4 — tp_resolver backward compatibility.

Verifies that `tp_logic: fixed_rr` (default when YAML omits the block) produces
the exact same TP price as the legacy inline arithmetic in
setup_engine_v2._calculate_price_levels. Byte-identical float output is
required so pre-sprint YAMLs keep behaving as before Option A v2 landed.
"""
from __future__ import annotations

from engines.execution.tp_resolver import resolve_tp_price


def _legacy_fixed_rr_long(entry: float, sl: float, tp1_rr: float) -> float:
    risk = entry - sl
    return entry + risk * tp1_rr


def _legacy_fixed_rr_short(entry: float, sl: float, tp1_rr: float) -> float:
    risk = sl - entry
    return entry - risk * tp1_rr


def test_fixed_rr_long_matches_legacy_byte_identical():
    tp, reason = resolve_tp_price(
        tp_logic="fixed_rr",
        tp_logic_params=None,
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=448.0,
        direction="LONG",
        bars=(),
    )
    assert tp == _legacy_fixed_rr_long(450.0, 448.0, 2.0)
    assert reason == "fixed_rr"


def test_fixed_rr_short_matches_legacy_byte_identical():
    tp, reason = resolve_tp_price(
        tp_logic="fixed_rr",
        tp_logic_params=None,
        tp1_rr=3.0,
        entry_price=400.0,
        sl_price=402.5,
        direction="SHORT",
        bars=(),
    )
    assert tp == _legacy_fixed_rr_short(400.0, 402.5, 3.0)
    assert reason == "fixed_rr"


def test_fixed_rr_ignores_structure_pivots():
    """fixed_rr must not consult pivots even if the caller provides them
    (keeps the two code paths strictly decoupled)."""
    from engines.features.pivot import Pivot
    from datetime import datetime

    bogus_pivots = {
        "k3": [
            Pivot(index=0, price=500.0, type="high", timestamp=datetime(2025, 7, 15)),
        ],
    }
    tp, reason = resolve_tp_price(
        tp_logic="fixed_rr",
        tp_logic_params={"draw_type": "swing_k3"},
        tp1_rr=2.0,
        entry_price=450.0,
        sl_price=448.0,
        direction="LONG",
        bars=(),
        structure_pivots=bogus_pivots,
    )
    assert tp == 454.0  # purely RR, not 500
    assert reason == "fixed_rr"


def test_unknown_tp_logic_raises():
    import pytest

    with pytest.raises(ValueError):
        resolve_tp_price(
            tp_logic="swing_target",  # explicitly out of scope this sprint
            tp_logic_params=None,
            tp1_rr=2.0,
            entry_price=450.0,
            sl_price=448.0,
            direction="LONG",
            bars=(),
        )


def test_sl_distance_must_be_positive():
    import pytest

    with pytest.raises(ValueError):
        resolve_tp_price(
            tp_logic="fixed_rr",
            tp_logic_params=None,
            tp1_rr=2.0,
            entry_price=450.0,
            sl_price=450.0,
            direction="LONG",
            bars=(),
        )
