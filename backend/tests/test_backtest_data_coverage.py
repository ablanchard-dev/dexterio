"""Couverture données backtest (preflight)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from utils.backtest_data_coverage import (
    check_backtest_data_coverage,
    max_gap_minutes_same_utc_day,
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


def test_same_utc_day_gap_ignores_overnight_calendar_change() -> None:
    """Vendredi → lundi : grand écart en 'toutes paires', ignoré si même jour UTC seulement par jour."""
    t = pd.to_datetime(
        [
            "2025-01-03 20:00:00+00:00",
            "2025-01-03 20:01:00+00:00",
            "2025-01-06 14:30:00+00:00",
        ],
        utc=True,
    )
    s = pd.Series(t)
    assert max_intraday_gap_minutes(s) > 100.0
    assert max_gap_minutes_same_utc_day(s) == 1.0


def test_coverage_fails_when_first_bar_after_start(tmp_path: Path) -> None:
    p = tmp_path / "SPY.parquet"
    _write_1m_parquet(p, "2025-01-05", "2025-01-31 23:59:00")
    r = check_backtest_data_coverage(
        data_paths=[str(p)],
        symbols=["SPY"],
        start_date="2025-01-01",
        end_date="2025-01-31",
        htf_warmup_days=0,
        max_gap_warn_minutes=None,
    )
    assert r["ok"] is False
    assert any("après start" in e for e in r["errors"])


def test_ignore_warmup_check_allows_late_data_start(tmp_path: Path) -> None:
    """Données commencent à start mais pas assez tôt pour warmup : OK si ignore_warmup_check."""
    p = tmp_path / "SPY.parquet"
    _write_1m_parquet(p, "2025-01-01", "2025-02-01 23:59:00")
    r_fail = check_backtest_data_coverage(
        data_paths=[str(p)],
        symbols=["SPY"],
        start_date="2025-01-01",
        end_date="2025-01-31",
        htf_warmup_days=30,
        max_gap_warn_minutes=None,
    )
    assert r_fail["ok"] is False
    r_ok = check_backtest_data_coverage(
        data_paths=[str(p)],
        symbols=["SPY"],
        start_date="2025-01-01",
        end_date="2025-01-31",
        htf_warmup_days=30,
        max_gap_warn_minutes=None,
        ignore_warmup_check=True,
    )
    assert r_ok["ok"] is True
    assert any("warmup HTF" in w for w in r_ok["warnings"])
