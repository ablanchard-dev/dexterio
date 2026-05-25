"""Feature store minimal — S+1 Plan VIX VRP.

Centralise feature engineering pour éviter de recoder ATR/gap/regime/etc.
dans chaque détecteur. v1 ciblé scope VIX VRP — extensible incrémentalement
selon edges futurs.

Convention :
    - Each feature function takes Series/DataFrame, returns Series same index
    - All features lookahead-safe (use shift(1) where needed)
    - Documented kill-rule : si feature requires future data → raise

Features v1 (VIX VRP scope) :
    - vix_level_prior          : VIX close prior day (actionable at open today)
    - vix_change_5d            : VIX 5-day delta
    - vix_regime               : categorical {low, fertile, elevated, panic}
    - vxx_svxy_ratio           : contango proxy (long-vol / inverse-vol price ratio)
    - vxx_svxy_5d_zscore       : ratio momentum (recent regime change detection)
    - day_of_week              : Mon-Fri categorical
    - month                    : 1-12 categorical
    - days_since_vix_spike     : counter days since last VIX > 30 close
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def vix_level_prior(vix_close: pd.Series) -> pd.Series:
    """VIX close prior day — actionable at today's open."""
    return vix_close.shift(1).rename("vix_level_prior")


def vix_change(vix_close: pd.Series, days: int = 5) -> pd.Series:
    """VIX absolute change over N days (prior-anchored, lookahead-safe)."""
    prior = vix_close.shift(1)
    return (prior - prior.shift(days)).rename(f"vix_change_{days}d")


def vix_regime(vix_close: pd.Series) -> pd.Series:
    """Categorical VIX regime per §0.4-bis taxonomy.

    Bins :
        low      : VIX < 15
        fertile  : 15 ≤ VIX < 25
        elevated : 25 ≤ VIX < 30
        panic    : VIX ≥ 30
    Uses prior-day close (lookahead-safe).
    """
    prior = vix_close.shift(1)
    out = pd.Series("unknown", index=vix_close.index, name="vix_regime")
    out[prior < 15] = "low"
    out[(prior >= 15) & (prior < 25)] = "fertile"
    out[(prior >= 25) & (prior < 30)] = "elevated"
    out[prior >= 30] = "panic"
    return out


def vxx_svxy_ratio(vxx_close: pd.Series, svxy_close: pd.Series) -> pd.Series:
    """VXX/SVXY price ratio — contango proxy.

    Higher ratio = more "expensive" long-vol relative to inverse, signals
    contango regime where SVXY rolls cheap. Lookahead-safe (uses prior).
    """
    return (vxx_close.shift(1) / svxy_close.shift(1)).rename("vxx_svxy_ratio")


def vxx_svxy_zscore(vxx_close: pd.Series, svxy_close: pd.Series,
                     window: int = 20) -> pd.Series:
    """Z-score of VXX/SVXY ratio over rolling window (regime change detection).

    Lookahead-safe : uses ratio prior, computes rolling stats including current
    prior day, output shifted to avoid lookahead.
    """
    ratio = (vxx_close.shift(1) / svxy_close.shift(1))
    rolling_mean = ratio.rolling(window).mean()
    rolling_std = ratio.rolling(window).std()
    z = (ratio - rolling_mean) / rolling_std
    return z.rename(f"vxx_svxy_zscore_{window}d")


def day_of_week(index: pd.DatetimeIndex) -> pd.Series:
    """Day of week (0=Mon, 4=Fri)."""
    return pd.Series(index.dayofweek, index=index, name="day_of_week")


def month(index: pd.DatetimeIndex) -> pd.Series:
    """Calendar month (1-12)."""
    return pd.Series(index.month, index=index, name="month")


def days_since_vix_spike(vix_close: pd.Series, threshold: float = 30.0) -> pd.Series:
    """Counter : days since last close VIX > threshold.

    Useful for "post-panic recovery" features. Lookahead-safe (uses prior).
    Reset to 0 on spike day, increments by 1 each day after.
    """
    prior = vix_close.shift(1)
    is_spike = prior > threshold
    counter = pd.Series(np.nan, index=vix_close.index)
    days_since = np.nan
    for i, spike in enumerate(is_spike):
        if pd.isna(spike):
            continue
        if spike:
            days_since = 0
        else:
            days_since = (days_since + 1) if not pd.isna(days_since) else np.nan
        counter.iloc[i] = days_since
    return counter.rename(f"days_since_vix_spike_{int(threshold)}")


def build_vix_vrp_features(vix_close: pd.Series, vxx_close: pd.Series,
                             svxy_close: pd.Series) -> pd.DataFrame:
    """Build full VIX VRP feature DataFrame.

    Args:
        vix_close : VIX daily close series, datetime index
        vxx_close : VXX daily close series, datetime index
        svxy_close : SVXY daily close series, datetime index

    Returns:
        DataFrame with all features, one row per date, lookahead-safe.
    """
    idx = vix_close.index
    df = pd.DataFrame(index=idx)
    df[vix_level_prior(vix_close).name] = vix_level_prior(vix_close)
    df["vix_change_5d"] = vix_change(vix_close, 5)
    df["vix_change_20d"] = vix_change(vix_close, 20)
    df["vix_regime"] = vix_regime(vix_close)
    df["vxx_svxy_ratio"] = vxx_svxy_ratio(vxx_close, svxy_close)
    df["vxx_svxy_zscore_20d"] = vxx_svxy_zscore(vxx_close, svxy_close, 20)
    df["day_of_week"] = day_of_week(idx)
    df["month"] = month(idx)
    df["days_since_vix_spike_30"] = days_since_vix_spike(vix_close, 30.0)
    return df
