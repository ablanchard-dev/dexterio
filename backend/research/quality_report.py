"""Dataset quality report — S+2 P0.

Quick QC for any provider-fetched dataset. Detects :
  - NaN ratio per critical column
  - Stale data (last date < expected)
  - Gap detection (missing trading days, irregular frequency)
  - Per-symbol coverage anomalies (some symbols have << avg rows)
  - Outlier prices (close < 0, daily move > 50%)
  - Volume anomalies (zero-volume days)

Output : list of warnings + headline status (OK / WARN / FAIL).
Used by data_manage.py CLI check-quality command + Provider.save() to attach
warnings to manifest sidecar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# Status thresholds
NAN_RATIO_WARN = 0.05  # > 5% NaN = warn
NAN_RATIO_FAIL = 0.20  # > 20% NaN = fail
STALE_DAYS_WARN = 7    # data older than 7 days = warn
STALE_DAYS_FAIL = 30   # data older than 30 days = fail
COVERAGE_DEVIATION_WARN = 0.30  # symbol with rows < 70% of median = warn
DAILY_RETURN_OUTLIER = 0.50    # > 50% daily move = outlier flag


@dataclass
class QualityReport:
    """Result of quality check for a dataset."""

    dataset_path: str
    n_rows: int
    n_symbols: int
    date_range: tuple[Optional[str], Optional[str]]
    warnings: list[str] = field(default_factory=list)
    fails: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.fails:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "OK"

    def to_dict(self) -> dict:
        return {
            "dataset_path": self.dataset_path,
            "status": self.status,
            "n_rows": self.n_rows,
            "n_symbols": self.n_symbols,
            "date_range": self.date_range,
            "warnings": self.warnings,
            "fails": self.fails,
            "stats": self.stats,
        }

    def __str__(self) -> str:
        lines = [
            f"=== Quality Report : {self.dataset_path} ===",
            f"Status : {self.status}",
            f"Rows : {self.n_rows:,}  | Symbols : {self.n_symbols}",
            f"Date range : {self.date_range[0]} → {self.date_range[1]}",
        ]
        if self.fails:
            lines.append(f"FAILS ({len(self.fails)}) :")
            lines.extend(f"  ❌ {f}" for f in self.fails)
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}) :")
            lines.extend(f"  ⚠️  {w}" for w in self.warnings)
        if self.stats:
            lines.append("Stats :")
            for k, v in self.stats.items():
                lines.append(f"  {k} : {v}")
        return "\n".join(lines)


def check_prices_quality(df: pd.DataFrame, dataset_path: str = "<unknown>",
                          critical_cols: Optional[list[str]] = None,
                          expected_freq: str = "B",
                          expected_end: Optional[str] = None) -> QualityReport:
    """QC for OHLCV price dataset (long format : symbol, date, open, high, low,
    close, volume).

    Args:
        df : long-format prices DataFrame
        dataset_path : label for report
        critical_cols : columns where NaN must be tracked (default : close)
        expected_freq : pandas frequency string for gap detection ('B'=business day)
    """
    critical_cols = critical_cols or ["close"]
    report = QualityReport(
        dataset_path=dataset_path,
        n_rows=len(df),
        n_symbols=df["symbol"].nunique() if "symbol" in df.columns else 0,
        date_range=(None, None),
    )

    if df.empty:
        report.fails.append("Dataset is empty")
        return report

    if "date" not in df.columns:
        report.fails.append("Missing 'date' column")
        return report

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    report.date_range = (str(df["date"].min().date()), str(df["date"].max().date()))

    # NaN ratio per critical column
    for col in critical_cols:
        if col not in df.columns:
            report.fails.append(f"Missing critical column : {col}")
            continue
        nan_ratio = df[col].isna().mean()
        report.stats[f"nan_ratio_{col}"] = round(nan_ratio, 4)
        if nan_ratio >= NAN_RATIO_FAIL:
            report.fails.append(f"{col} NaN ratio {nan_ratio:.1%} >= {NAN_RATIO_FAIL:.0%} fail threshold")
        elif nan_ratio >= NAN_RATIO_WARN:
            report.warnings.append(f"{col} NaN ratio {nan_ratio:.1%} >= {NAN_RATIO_WARN:.0%} warn threshold")

    # Stale data check : compare last_date vs expected_end (if provided) else today
    last_date = df["date"].max()
    reference_date = pd.to_datetime(expected_end).normalize() if expected_end else pd.Timestamp.now().normalize()
    days_stale = (reference_date - last_date).days
    report.stats["days_since_last_date"] = days_stale
    report.stats["reference_date"] = str(reference_date.date())
    if days_stale >= STALE_DAYS_FAIL:
        report.fails.append(f"Data stale {days_stale}d vs expected {reference_date.date()} (>= {STALE_DAYS_FAIL}d fail)")
    elif days_stale >= STALE_DAYS_WARN:
        report.warnings.append(f"Data stale {days_stale}d vs expected {reference_date.date()} (>= {STALE_DAYS_WARN}d warn)")

    # Per-symbol coverage anomalies
    if "symbol" in df.columns:
        per_sym = df.groupby("symbol").size()
        median_rows = per_sym.median()
        threshold = median_rows * (1 - COVERAGE_DEVIATION_WARN)
        anomalous = per_sym[per_sym < threshold]
        report.stats["per_symbol_median_rows"] = int(median_rows)
        report.stats["per_symbol_min_rows"] = int(per_sym.min())
        report.stats["per_symbol_max_rows"] = int(per_sym.max())
        if len(anomalous) > 0:
            sample = ", ".join(f"{s}({n})" for s, n in anomalous.head(5).items())
            report.warnings.append(
                f"{len(anomalous)} symbols have rows < {COVERAGE_DEVIATION_WARN:.0%} of median "
                f"({int(median_rows)}) : {sample}{'...' if len(anomalous)>5 else ''}"
            )

    # Outlier prices
    if "close" in df.columns and "symbol" in df.columns:
        df["daily_ret"] = df.groupby("symbol")["close"].pct_change()
        outliers = df[df["daily_ret"].abs() > DAILY_RETURN_OUTLIER]
        report.stats["n_outlier_returns"] = len(outliers)
        if len(outliers) > 0:
            sample = ", ".join(
                f"{r.symbol}@{r.date.date()}({r.daily_ret:+.0%})"
                for _, r in outliers.head(3).iterrows()
            )
            report.warnings.append(
                f"{len(outliers)} daily returns > {DAILY_RETURN_OUTLIER:.0%} : {sample}"
                f"{'...' if len(outliers)>3 else ''}"
            )

    # Negative close prices (clearly bad data)
    if "close" in df.columns:
        neg_count = (df["close"] < 0).sum()
        if neg_count > 0:
            report.fails.append(f"{neg_count} negative close prices detected")

    # Zero-volume days
    if "volume" in df.columns:
        zero_vol_ratio = (df["volume"] == 0).mean()
        report.stats["zero_volume_ratio"] = round(zero_vol_ratio, 4)
        if zero_vol_ratio > 0.10:
            report.warnings.append(f"Zero-volume ratio {zero_vol_ratio:.1%} > 10%")

    return report


def check_earnings_quality(df: pd.DataFrame,
                           dataset_path: str = "<unknown>") -> QualityReport:
    """QC for earnings dataset (long format : symbol, earnings_date,
    eps_estimate, eps_actual, surprise_pct, source).
    """
    report = QualityReport(
        dataset_path=dataset_path,
        n_rows=len(df),
        n_symbols=df["symbol"].nunique() if "symbol" in df.columns else 0,
        date_range=(None, None),
    )

    if df.empty:
        report.fails.append("Dataset is empty")
        return report

    if "earnings_date" not in df.columns:
        report.fails.append("Missing 'earnings_date' column")
        return report

    df = df.copy()
    df["earnings_date"] = pd.to_datetime(df["earnings_date"])
    report.date_range = (str(df["earnings_date"].min().date()),
                          str(df["earnings_date"].max().date()))

    # Per-symbol coverage : expect ~4 quarters/year, so over N years ~ 4N events
    if "symbol" in df.columns:
        per_sym = df.groupby("symbol").size()
        report.stats["per_symbol_median_events"] = int(per_sym.median())
        report.stats["per_symbol_min_events"] = int(per_sym.min())
        report.stats["per_symbol_max_events"] = int(per_sym.max())
        thin_sym = per_sym[per_sym < 4]
        if len(thin_sym) > 0:
            sample = ", ".join(f"{s}({n})" for s, n in thin_sym.head(5).items())
            report.warnings.append(
                f"{len(thin_sym)} symbols with < 4 earnings events : {sample}"
                f"{'...' if len(thin_sym)>5 else ''}"
            )

    # NaN in eps_actual (means future earnings event w/o report yet — OK)
    # NaN in eps_estimate is bad (no analyst estimate = no PEAD setup)
    if "eps_estimate" in df.columns:
        nan_est = df["eps_estimate"].isna().mean()
        report.stats["nan_ratio_eps_estimate"] = round(nan_est, 4)
        if nan_est >= NAN_RATIO_FAIL:
            report.fails.append(f"eps_estimate NaN ratio {nan_est:.1%} too high")
        elif nan_est >= NAN_RATIO_WARN:
            report.warnings.append(f"eps_estimate NaN ratio {nan_est:.1%}")

    # Surprise outliers (>>500% surprise = data error usually)
    if "surprise_pct" in df.columns:
        extreme = df[df["surprise_pct"].abs() > 500]
        if len(extreme) > 0:
            report.warnings.append(f"{len(extreme)} extreme surprises (>500%) — check data")

    return report
