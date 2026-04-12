"""Couverture données backtest (preflight)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from utils.backtest_data_coverage import (
    check_backtest_data_coverage,
    max_intraday_gap_minutes,
    parquet_datetime_bounds,
)


def _write_1m_parquet(path: Path, start: str, end: str, freq: str = "1min") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    idx = pd.date_range(start, end, freq=freq, tz="UTC")
    df = pd.DataFrame({"datetime": idx})
    df.to_parquet(path, index=False)


def test_parquet_datetime_bounds(tmp_path: Path) -> None:
    p = tmp_path / "SPY.parquet"
    _write_1m_parquet(p, "2025-01-02", "2025-01-02 23:59:00")
    b = parquet_datetime_bounds(p)
    assert b["exists"] and b["rows"] > 0
    assert "2025-01-02" in b["min_utc"]


def test_coverage_ok_with_warmup(tmp_path: Path) -> None:
    p = tmp_path / "SPY.parquet"
    _write_1m_parquet(p, "2024-11-01", "2025-02-01 23:59:00")
    r = check_backtest_data_coverage(
        data_paths=[str(p)],
        symbols=["SPY"],
        start_date="2025-01-01",
        end_date="2025-01-31",
        htf_warmup_days=30,
        max_gap_warn_minutes=None,
    )
    assert r["ok"] is True
    assert r["errors"] == []


def test_coverage_fails_short_data(tmp_path: Path) -> None:
    p = tmp_path / "SPY.parquet"
    _write_1m_parquet(p, "2025-01-01", "2025-01-15 23:59:00")
    r = check_backtest_data_coverage(
        data_paths=[str(p)],
        symbols=["SPY"],
        start_date="2025-01-01",
        end_date="2025-01-31",
        htf_warmup_days=0,
        max_gap_warn_minutes=None,
    )
    assert r["ok"] is False
    assert any("trop courtes" in e for e in r["errors"])


def test_max_gap_detects_hole() -> None:
    t = pd.to_datetime(
        ["2025-01-01 09:30:00+00:00", "2025-01-01 09:35:00+00:00"],
        utc=True,
    )
    assert max_intraday_gap_minutes(pd.Series(t)) == 5.0
