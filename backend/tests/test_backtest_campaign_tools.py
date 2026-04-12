"""Outils campagne backtest : compare summaries, walk-forward léger, audits."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from utils.backtest_leakage_audit import audit_trades_parquet_temporal
from utils.mini_lab_summary_compare import compare_mini_lab_summaries
from utils.walk_forward_light import walk_forward_two_splits_expanding


def test_walk_forward_two_splits_shape() -> None:
    rep = walk_forward_two_splits_expanding("2025-08-01", "2025-08-31")
    assert rep["schema_version"] == "WalkForwardLightV0"
    assert len(rep["splits"]) == 2
    assert rep["splits"][0]["test"]["start_date"] >= rep["splits"][0]["train"]["start_date"]
    assert rep["splits"][1]["train"]["end_date"] >= rep["splits"][0]["train"]["end_date"]


def test_walk_forward_too_short() -> None:
    with pytest.raises(ValueError, match="8 jours"):
        walk_forward_two_splits_expanding("2025-08-01", "2025-08-05")


def test_compare_mini_lab_summaries_funnel_delta() -> None:
    a = {
        "run_id": "a",
        "start_date": "2025-11-01",
        "end_date": "2025-11-07",
        "total_trades": 10,
        "final_capital": "10000",
        "funnel": {"News_Fade": {"matches": 5, "setups_created": 3, "after_risk": 2, "trades": 1}},
    }
    b = {
        "run_id": "b",
        "start_date": "2025-11-01",
        "end_date": "2025-11-07",
        "total_trades": 12,
        "final_capital": "10100",
        "funnel": {"News_Fade": {"matches": 8, "setups_created": 3, "after_risk": 2, "trades": 2}},
    }
    r = compare_mini_lab_summaries(a, b)
    assert r["schema_version"] == "MiniLabSummaryCompareV0"
    assert r["total_trades"]["delta"] == 2
    nf = r["funnel_by_playbook"]["News_Fade"]
    assert nf["matches"]["delta"] == 3
    assert nf["trades"]["delta"] == 1


def test_audit_trades_temporal_ok_and_bad(tmp_path: Path) -> None:
    ok = pd.DataFrame(
        {
            "timestamp_entry": pd.to_datetime(["2025-01-01 10:00:00+00:00"]),
            "timestamp_exit": pd.to_datetime(["2025-01-01 11:00:00+00:00"]),
        }
    )
    p_ok = tmp_path / "t_ok.parquet"
    ok.to_parquet(p_ok, index=False)
    r_ok = audit_trades_parquet_temporal(p_ok)
    assert r_ok["ok"] is True

    bad = pd.DataFrame(
        {
            "timestamp_entry": pd.to_datetime(["2025-01-01 12:00:00+00:00"]),
            "timestamp_exit": pd.to_datetime(["2025-01-01 11:00:00+00:00"]),
        }
    )
    p_bad = tmp_path / "t_bad.parquet"
    bad.to_parquet(p_bad, index=False)
    r_bad = audit_trades_parquet_temporal(p_bad)
    assert r_bad["ok"] is False
