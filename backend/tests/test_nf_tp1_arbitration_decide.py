"""Tests décision pure decide_nf_tp1_arbitration (chargement dynamique du script)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
_agg_path = backend_dir / "scripts" / "aggregate_nf_tp1_arbitration.py"
_spec = importlib.util.spec_from_file_location("aggregate_nf_tp1_arbitration", _agg_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
decide_nf_tp1_arbitration = _mod.decide_nf_tp1_arbitration


def test_switch_when_1p50_better_aligned_sum_r() -> None:
    d, _ = decide_nf_tp1_arbitration(
        expectancy_1p00=-0.05,
        expectancy_1p50=-0.02,
        sum_r_1p00=-4.25,
        sum_r_1p50=-1.70,
        nf_trades_1p00=85,
        nf_trades_1p50=85,
        epsilon_er=0.015,
    )
    assert d == "SWITCH_TO_1P5R"


def test_keep_1p0_when_better_aligned_sum_r() -> None:
    d, _ = decide_nf_tp1_arbitration(
        expectancy_1p00=0.04,
        expectancy_1p50=0.01,
        sum_r_1p00=3.4,
        sum_r_1p50=0.85,
        nf_trades_1p00=85,
        nf_trades_1p50=85,
        epsilon_er=0.015,
    )
    assert d == "KEEP_1P0R"


def test_unresolved_tie_expectancy() -> None:
    d, _ = decide_nf_tp1_arbitration(
        expectancy_1p00=-0.040,
        expectancy_1p50=-0.041,
        sum_r_1p00=-3.4,
        sum_r_1p50=-3.5,
        nf_trades_1p00=85,
        nf_trades_1p50=85,
        epsilon_er=0.015,
    )
    assert d == "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA"


def test_trade_count_mismatch_does_not_block_switch() -> None:
    """L'écart de cardinal n'invalide plus la décision (diagnostic séparé)."""
    d, _ = decide_nf_tp1_arbitration(
        expectancy_1p00=-0.05,
        expectancy_1p50=-0.02,
        sum_r_1p00=-4.25,
        sum_r_1p50=-1.70,
        nf_trades_1p00=85,
        nf_trades_1p50=86,
        epsilon_er=0.015,
    )
    assert d == "SWITCH_TO_1P5R"


def test_unresolved_contradictory_signs() -> None:
    d, _ = decide_nf_tp1_arbitration(
        expectancy_1p00=-0.05,
        expectancy_1p50=-0.02,
        sum_r_1p00=-2.0,
        sum_r_1p50=-5.0,
        nf_trades_1p00=40,
        nf_trades_1p50=40,
        epsilon_er=0.015,
    )
    assert d == "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA"
