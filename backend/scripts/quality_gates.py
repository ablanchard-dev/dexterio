"""Quality gates for intraday 1-minute datasets (P0.6.3).

Design goals (user requirements):
- Enforce a single timezone on timestamps (UTC)
- Ensure 0 duplicate timestamps after merge
- Validate OHLCV non-NaN during RTH (computed in US/Eastern)
- Produce a per-day missing bars report and tag corrupted days (>5% missing)

This module is intentionally dependency-light and can be imported by scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pytz


ET_TZ = pytz.timezone("US/Eastern")
UTC_TZ = pytz.UTC


@dataclass(frozen=True)
class RTHSpec:
    start_hm: time = time(9, 30)
    end_hm: time = time(16, 0)  # end exclusive
    expected_bars: int = 390


def normalize_datetime_to_utc(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a timezone-aware UTC 'datetime' column."""
    if "datetime" not in df.columns:
        raise ValueError("Missing required column: datetime")

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")

    if out["datetime"].isna().any():
        raise ValueError("Found NaT values in datetime column")

    # If tz-aware -> convert to UTC; if naive -> assume UTC and localize.
    if getattr(out["datetime"].dt, "tz", None) is not None:
        out["datetime"] = out["datetime"].dt.tz_convert(UTC_TZ)
    else:
        out["datetime"] = out["datetime"].dt.tz_localize(UTC_TZ)

    return out


def _rth_filter_et(dt_series_utc: pd.Series, rth: RTHSpec) -> pd.Series:
    dt_et = dt_series_utc.dt.tz_convert(ET_TZ)
    t = dt_et.dt.time
    # End exclusive to yield exactly 390 expected minutes.
    return (t >= rth.start_hm) & (t < rth.end_hm)


def compute_daily_missing_bars(
    df_utc: pd.DataFrame,
    start: date,
    end: date,
    *,
    max_missing_pct: float = 5.0,
    rth: RTHSpec = RTHSpec(),
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Compute per-day missing bars % during RTH.

    We iterate over the *calendar days* in [start, end) (end exclusive).
    Only weekdays are considered; weekends are skipped.

    Note: market holidays are not filtered out (no external calendar). They will
    typically appear as 100% missing if weekday.
    """

    if df_utc.empty:
        return [], []

    df_utc = df_utc.copy()
    df_utc["datetime"] = pd.to_datetime(df_utc["datetime"])

    # Precompute RTH-only view in ET so date boundaries are correct.
    dt_et = df_utc["datetime"].dt.tz_convert(ET_TZ)
    df_utc["date_et"] = dt_et.dt.date
    df_utc["is_rth"] = _rth_filter_et(df_utc["datetime"], rth)

    daily_rows: List[Dict[str, Any]] = []
    corrupted_days: List[str] = []

    cur = start
    while cur < end:
        if cur.weekday() >= 5:  # weekend
            cur = date.fromordinal(cur.toordinal() + 1)
            continue

        day_df = df_utc[(df_utc["date_et"] == cur) & (df_utc["is_rth"])].copy()
        actual = int(day_df["datetime"].nunique())
        expected = int(rth.expected_bars)
        missing = max(0, expected - actual)
        missing_pct = (missing / expected) * 100.0 if expected else 0.0

        # OHLCV non-NaN on RTH
        ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in day_df.columns]
        non_nan_ok = True
        if ohlcv_cols:
            non_nan_ok = not day_df[ohlcv_cols].isna().any().any()

        corrupted = (missing_pct > max_missing_pct) or (not non_nan_ok)
        if corrupted:
            corrupted_days.append(cur.isoformat())

        daily_rows.append(
            {
                "date_et": cur.isoformat(),
                "expected_bars": expected,
                "actual_bars": actual,
                "missing_bars": missing,
                "missing_pct": round(missing_pct, 3),
                "ohlcv_non_nan_rth": bool(non_nan_ok),
                "corrupted": bool(corrupted),
            }
        )

        cur = date.fromordinal(cur.toordinal() + 1)

    return daily_rows, corrupted_days


def run_quality_gates(
    df: pd.DataFrame,
    *,
    symbol: str,
    start: date,
    end: date,
    max_missing_pct: float = 5.0,
) -> Dict[str, Any]:
    """Run the minimum required quality gates and return a JSON-serializable report."""

    report: Dict[str, Any] = {
        "symbol": symbol,
        "total_bars": int(len(df)),
        "date_range": {
            "start": None,
            "end": None,
        },
        "gates": {},
        "daily_missing": [],
        "corrupted_days": [],
        "passed": True,
        "warnings": [],
    }

    if df.empty:
        report["passed"] = False
        report["warnings"].append("empty_dataframe")
        return report

    # Gate (1): tz unique (UTC)
    tz_values = df["datetime"].apply(lambda x: str(x.tzinfo) if getattr(x, "tzinfo", None) else "naive").unique()
    tz_gate = (len(tz_values) == 1) and ("UTC" in str(tz_values[0]))
    report["gates"]["timezone_utc"] = {"passed": bool(tz_gate), "values": [str(v) for v in tz_values]}

    # Gate (2): 0 duplicates
    dup_count = int(df["datetime"].duplicated().sum())
    report["gates"]["no_duplicate_timestamps"] = {"passed": dup_count == 0, "duplicates": dup_count}

    # Gate (3): OHLCV non-NaN sur RTH
    required_cols = ["open", "high", "low", "close", "volume"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        report["gates"]["required_ohlcv_columns"] = {"passed": False, "missing": missing_cols}
    else:
        # Check non-NaN on RTH only
        rth_mask = _rth_filter_et(df["datetime"], RTHSpec())
        rth_df = df.loc[rth_mask, required_cols]
        any_nan_rth = bool(rth_df.isna().any().any()) if not rth_df.empty else True
        report["gates"]["ohlcv_non_nan_rth"] = {"passed": not any_nan_rth, "nan_in_rth": any_nan_rth}

    # Gate (4): missing bars report + corrupted tagging
    daily_missing, corrupted_days = compute_daily_missing_bars(
        df,
        start=start,
        end=end,
        max_missing_pct=max_missing_pct,
    )
    report["daily_missing"] = daily_missing
    report["corrupted_days"] = corrupted_days

    if df.empty:
        report["date_range"]["start"] = None
        report["date_range"]["end"] = None
    else:
        report["date_range"]["start"] = df["datetime"].min().isoformat()
        report["date_range"]["end"] = df["datetime"].max().isoformat()

    # Overall pass
    report["passed"] = all(g.get("passed", True) for g in report["gates"].values())

    return report
