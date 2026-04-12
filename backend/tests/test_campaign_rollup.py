"""Rollup agrégats mini_lab_summary."""
from __future__ import annotations

import json
from pathlib import Path

from utils.campaign_rollup import rollup_summaries_under_base


def test_rollup_nested_two_runs(tmp_path: Path) -> None:
    root = tmp_path / "camp"
    for label, tt, ex in (("w1", 10, 0.5), ("w2", 20, -0.25)):
        d = root / label
        d.mkdir(parents=True)
        (d / f"mini_lab_summary_{label}.json").write_text(
            json.dumps(
                {
                    "run_id": label,
                    "start_date": "2025-11-01",
                    "end_date": "2025-11-07",
                    "total_trades": tt,
                    "data_coverage_ok": True,
                    "trade_metrics_parquet": {
                        "schema_version": "MiniLabTradeMetricsParquetV0",
                        "expectancy_r": ex,
                        "sum_pnl_dollars": float(tt) * ex,
                    },
                }
            ),
            encoding="utf-8",
        )
    rep = rollup_summaries_under_base(root, logical_name="camp")
    assert rep["schema_version"] == "CampaignRollupV0"
    assert rep["layout"] == "nested"
    assert rep["run_count"] == 2
    assert rep["total_trades_sum"] == 30
    assert rep["all_data_coverage_ok"] is True
    # (10*0.5 + 20*-0.25) / 30 = (5 - 5) / 30 = 0
    assert abs(float(rep["expectancy_r_weighted_by_trades"]) - 0.0) < 1e-9


def test_rollup_flat_single(tmp_path: Path) -> None:
    d = tmp_path / "solo"
    d.mkdir()
    (d / "mini_lab_summary_solo.json").write_text(
        json.dumps(
            {
                "run_id": "solo",
                "total_trades": 5,
                "data_coverage_ok": True,
                "trade_metrics_parquet": {"expectancy_r": 1.0, "sum_pnl_dollars": 5.0},
            }
        ),
        encoding="utf-8",
    )
    rep = rollup_summaries_under_base(d, logical_name="solo")
    assert rep["layout"] == "flat"
    assert rep["total_trades_sum"] == 5
    assert rep["expectancy_r_weighted_by_trades"] == 1.0
