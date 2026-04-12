"""Manifest et alignement trades — arbitrage NF tp1."""
from __future__ import annotations

from pathlib import Path

from utils.nf_tp1_arbitration_campaign import (
    analyze_nf_trade_count_alignment,
    build_campaign_manifest,
    campaign_dir_names,
    pair_status,
)


def test_expected_pair_count_is_12() -> None:
    m = build_campaign_manifest(mini_week=Path("/nonexistent"))
    assert m["expected_pair_count"] == 12
    assert m["global_status"] == "NOT_STARTED"


def test_pair_status_complete(tmp_path: Path) -> None:
    mini = tmp_path / "mini_week"
    c0, c1 = campaign_dir_names("aug2025")
    label = "202508_w01"
    run0 = f"miniweek_{c0}_{label}"
    run1 = f"miniweek_{c1}_{label}"
    d0 = mini / c0 / label
    d1 = mini / c1 / label
    d0.mkdir(parents=True)
    d1.mkdir(parents=True)
    (d0 / f"mini_lab_summary_{label}.json").write_text("{}", encoding="utf-8")
    (d1 / f"mini_lab_summary_{label}.json").write_text("{}", encoding="utf-8")
    (d0 / f"trades_{run0}_AGGRESSIVE_DAILY_SCALP.parquet").write_bytes(b"x")
    (d1 / f"trades_{run1}_AGGRESSIVE_DAILY_SCALP.parquet").write_bytes(b"y")
    st = pair_status(mini, "aug2025", label)
    assert st["status"] == "complete"


def test_analyze_trade_alignment_levels() -> None:
    assert analyze_nf_trade_count_alignment(85, 85)["alignment_level"] == "aligned"
    assert analyze_nf_trade_count_alignment(85, 86)["alignment_level"] == "minor"
    a = analyze_nf_trade_count_alignment(10, 20)
    assert a["alignment_level"] == "major"
    assert a["delta_abs"] == 10
