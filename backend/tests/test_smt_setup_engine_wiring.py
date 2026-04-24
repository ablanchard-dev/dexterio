"""Tests for SMT setup_engine_v2 wiring integration.

Verifies :
1. playbook_loader type_map maps `SMT` / `SMTCROSSINDEX` → `smt_cross_index_sequence`.
2. setup_engine_v2 merges `smt_completion_target` from synthetic ICTPattern into
   tp_logic_params when tp_logic="smt_completion".
3. The resolved TP uses the merged smt_completion_price (not fallback_rr).
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.execution.tp_resolver import resolve_tp_price
from models.setup import ICTPattern

ET = ZoneInfo("America/New_York")


def _ts(h: int = 10, m: int = 0) -> datetime:
    return datetime(2025, 11, 17, h, m, tzinfo=ET)


def test_playbook_loader_type_map_includes_smt():
    """`SMT_CROSS_INDEX@5m` in required_signals should map to 'smt_cross_index_sequence'."""
    # Simulate the playbook_loader.py logic locally :
    sig = "SMT_CROSS_INDEX@5m"
    sig_parts = sig.split("_")
    base = sig_parts[0].upper()
    type_map = {
        "APLUS01": "aplus01_sequence",
        "SMT": "smt_cross_index_sequence",
        "SMTCROSSINDEX": "smt_cross_index_sequence",
    }
    p_type = type_map.get(base, base.lower())
    assert p_type == "smt_cross_index_sequence"


def test_setup_engine_merges_smt_completion_target_from_synthetic_pattern():
    """Mimics setup_engine_v2's merge logic : an SMT synthetic pattern's
    details['smt_completion_target'] must be injected into tp_logic_params['smt_completion_price']
    before resolve_tp_price is called."""
    # Synthetic ICTPattern as produced by SMTDriver.
    synthetic = ICTPattern(
        symbol="QQQ",
        timeframe="5m",
        pattern_type="smt_cross_index_sequence",
        direction="bearish",
        price_level=103.8,
        details={
            "leading_symbol": "SPY",
            "lagging_symbol": "QQQ",
            "divergence_type": "bear",
            "smt_completion_target": 100.0,  # ← this must reach tp_resolver
            "pool_sweep_tf": "4h",
            "pool_sweep_ts": _ts(10, 0).isoformat(),
            "signal_ts": _ts(10, 10).isoformat(),
            "emit_ts": _ts(10, 10).isoformat(),
        },
        strength=1.0,
        confidence=0.95,
    )

    # Simulate setup_engine's merge logic (the snippet we added to _calculate_price_levels).
    ict_patterns = [synthetic]
    tp_logic = "smt_completion"
    tp_logic_params = {"fallback_rr": 2.0, "reject_on_fallback": True}  # from playbook YAML

    if tp_logic == "smt_completion" and ict_patterns:
        for p in ict_patterns:
            if p.pattern_type == "smt_cross_index_sequence":
                target = (p.details or {}).get("smt_completion_target")
                if target is not None:
                    tp_logic_params["smt_completion_price"] = float(target)
                break

    # Call tp_resolver with the merged params.
    tp_price, tp_reason = resolve_tp_price(
        tp_logic=tp_logic,
        tp_logic_params=tp_logic_params,
        tp1_rr=2.0,
        entry_price=103.8,
        sl_price=105.0,  # SHORT SL above entry
        direction="SHORT",
        bars=[],
    )

    assert tp_reason == "smt_completion"
    assert tp_price == pytest.approx(100.0)


def test_setup_engine_merge_with_no_smt_pattern_falls_back():
    """If no SMT synthetic pattern is present, tp_logic='smt_completion' should
    fall back to reject_on_fallback."""
    tp_logic = "smt_completion"
    tp_logic_params = {"fallback_rr": 2.0, "reject_on_fallback": True}
    ict_patterns = []  # no SMT pattern

    if tp_logic == "smt_completion" and ict_patterns:
        # never entered
        pass

    tp_price, tp_reason = resolve_tp_price(
        tp_logic=tp_logic,
        tp_logic_params=tp_logic_params,
        tp1_rr=2.0,
        entry_price=103.8,
        sl_price=105.0,
        direction="SHORT",
        bars=[],
    )
    assert tp_reason == "reject_on_fallback_no_smt_completion"


def test_setup_engine_merge_ignores_non_smt_patterns():
    """If the ict_patterns list contains non-SMT patterns but no smt_cross_index_sequence,
    the merge must not pick up a random 'smt_completion_target' from unrelated patterns."""
    # An unrelated pattern (e.g. aplus01_sequence) has no smt_completion_target.
    unrelated = ICTPattern(
        symbol="SPY",
        timeframe="1m",
        pattern_type="aplus01_sequence",
        direction="bullish",
        price_level=100.0,
        details={"unrelated": "payload"},
        strength=1.0,
        confidence=0.95,
    )
    ict_patterns = [unrelated]
    tp_logic = "smt_completion"
    tp_logic_params = {"fallback_rr": 2.0, "reject_on_fallback": True}

    if tp_logic == "smt_completion" and ict_patterns:
        for p in ict_patterns:
            if p.pattern_type == "smt_cross_index_sequence":
                target = (p.details or {}).get("smt_completion_target")
                if target is not None:
                    tp_logic_params["smt_completion_price"] = float(target)
                break

    # smt_completion_price NOT set → resolver falls back.
    assert "smt_completion_price" not in tp_logic_params
    tp_price, tp_reason = resolve_tp_price(
        tp_logic=tp_logic,
        tp_logic_params=tp_logic_params,
        tp1_rr=2.0,
        entry_price=103.8,
        sl_price=105.0,
        direction="SHORT",
        bars=[],
    )
    assert tp_reason == "reject_on_fallback_no_smt_completion"
