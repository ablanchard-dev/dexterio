"""Label factory minimal — S+1 Plan VIX VRP.

Transforme strategy returns en labels MFE/MAE/forward-return systémiques pour :
  - Évaluer ex-post peak excursion
  - Préparer ML metalabeling future (post-positive-edge only)
  - Diagnostics qualitatifs (e.g., "winners ride to MFE 3R, losers exit at -1R")

Convention :
    - All labels lookahead OK (we LOOK at future bars by definition for MFE/MAE)
    - Labels generated post-trade (not used for entry decision)
    - Forward windows : 5d, 20d (week / month)

v1 scope : strategy daily returns level (portfolio equity curve), not per-trade.
Per-trade granular labels = post Stage 1 PASS only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return(returns: pd.Series, horizon: int) -> pd.Series:
    """Forward cumulative return over N days.

    Lookahead INTENTIONAL (label generation, not feature).
    """
    cum = (1 + returns).rolling(horizon).apply(np.prod, raw=True) - 1
    return cum.shift(-(horizon - 1)).rename(f"forward_ret_{horizon}d")


def forward_mfe(returns: pd.Series, horizon: int) -> pd.Series:
    """Maximum Favorable Excursion over forward horizon.

    For a long position entered at t, MFE = max cumulative return reached in
    [t, t+horizon].
    """
    cum_returns = (1 + returns).cumprod()
    mfe = []
    for i in range(len(cum_returns)):
        if i + horizon > len(cum_returns):
            mfe.append(np.nan)
            continue
        window = cum_returns.iloc[i:i + horizon]
        entry = cum_returns.iloc[i] / (1 + returns.iloc[i])  # equity before entry day
        if entry == 0:
            mfe.append(np.nan)
            continue
        max_eq = window.max()
        mfe.append(max_eq / entry - 1)
    return pd.Series(mfe, index=returns.index, name=f"mfe_{horizon}d")


def forward_mae(returns: pd.Series, horizon: int) -> pd.Series:
    """Maximum Adverse Excursion over forward horizon.

    For a long position entered at t, MAE = min cumulative return in [t, t+h].
    """
    cum_returns = (1 + returns).cumprod()
    mae = []
    for i in range(len(cum_returns)):
        if i + horizon > len(cum_returns):
            mae.append(np.nan)
            continue
        window = cum_returns.iloc[i:i + horizon]
        entry = cum_returns.iloc[i] / (1 + returns.iloc[i])
        if entry == 0:
            mae.append(np.nan)
            continue
        min_eq = window.min()
        mae.append(min_eq / entry - 1)
    return pd.Series(mae, index=returns.index, name=f"mae_{horizon}d")


def capture_ratio_from_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Compute capture_ratio per trade : realized_R / peak_R.

    Captures whether the strategy is leaving R on the table (exit too early)
    OR letting winners turn into losers (exit too late).

    Args:
        trades_df : per-trade DataFrame with columns 'r_multiple' (realized R)
                    and 'peak_r' (max excursion in R).

    Returns:
        DataFrame with capture_ratio + diagnostic categorization :
            - 'edge_uncapturable' : peak_R < 0.5R (signal weak — fix signal)
            - 'exit_too_early' : peak_R > 1R, capture < 50% (signal OK, fix exit)
            - 'exit_too_late' : peak_R > 1R, realized < 0 (gourmandise — tighter trail/BE)
            - 'efficient' : capture > 70% (working as designed)
            - 'mixed' : middle cases
    """
    df = trades_df.copy()
    df["capture_ratio"] = df["r_multiple"] / df["peak_r"].replace(0, np.nan)

    # Diagnostic categorization
    def categorize(row) -> str:
        peak = row["peak_r"]
        realized = row["r_multiple"]
        if pd.isna(peak) or pd.isna(realized):
            return "unknown"
        if peak < 0.5:
            return "edge_uncapturable"
        if peak >= 1.0 and realized < 0:
            return "exit_too_late"
        if peak >= 1.0 and realized < peak * 0.5:
            return "exit_too_early"
        if realized >= peak * 0.7:
            return "efficient"
        return "mixed"

    df["capture_diagnostic"] = df.apply(categorize, axis=1)
    return df[["capture_ratio", "capture_diagnostic"]]


def capture_summary(trades_df: pd.DataFrame) -> dict:
    """Aggregate capture diagnostics for a trades dataframe.

    Returns a dict with per-category counts + median capture_ratio + headline
    diagnostic ('signal_weak' / 'exit_broken' / 'efficient' / 'mixed').
    """
    enriched = capture_ratio_from_trades(trades_df)
    cat_counts = enriched["capture_diagnostic"].value_counts().to_dict()
    n = len(enriched)
    if n == 0:
        return {"n": 0, "headline": "no_trades"}

    pct_uncapt = cat_counts.get("edge_uncapturable", 0) / n
    pct_early = cat_counts.get("exit_too_early", 0) / n
    pct_late = cat_counts.get("exit_too_late", 0) / n
    pct_eff = cat_counts.get("efficient", 0) / n

    if pct_uncapt > 0.5:
        headline = "signal_weak"
    elif pct_early > 0.4:
        headline = "exit_broken_too_early"
    elif pct_late > 0.3:
        headline = "exit_broken_too_late"
    elif pct_eff > 0.5:
        headline = "efficient"
    else:
        headline = "mixed"

    return {
        "n": n,
        "median_capture_ratio": float(enriched["capture_ratio"].median()),
        "categories": cat_counts,
        "pct_signal_weak": pct_uncapt,
        "pct_exit_early": pct_early,
        "pct_exit_late": pct_late,
        "pct_efficient": pct_eff,
        "headline": headline,
    }


def hit_threshold(returns: pd.Series, horizon: int, threshold: float) -> pd.Series:
    """Binary label : 1 if cumulative return reaches `threshold` within
    `horizon` days, 0 otherwise.

    Lookahead intentional. Threshold expressed as fraction (e.g., 0.05 = +5%).
    """
    cum_returns = (1 + returns).cumprod()
    hits = []
    for i in range(len(cum_returns)):
        if i + horizon > len(cum_returns):
            hits.append(np.nan)
            continue
        window = cum_returns.iloc[i:i + horizon]
        entry = cum_returns.iloc[i] / (1 + returns.iloc[i])
        if entry == 0:
            hits.append(np.nan)
            continue
        max_ret = window.max() / entry - 1
        hits.append(1 if max_ret >= threshold else 0)
    return pd.Series(hits, index=returns.index, name=f"hit_{int(threshold*100)}pct_{horizon}d")


def build_strategy_labels(returns: pd.Series, horizons: tuple = (5, 20)) -> pd.DataFrame:
    """Build full label DataFrame for a strategy daily return series.

    Args:
        returns : daily strategy returns (e.g., portfolio equity.pct_change())
        horizons : forward windows to evaluate (in days)

    Returns:
        DataFrame with columns forward_ret_*d, mfe_*d, mae_*d for each horizon.
    """
    df = pd.DataFrame(index=returns.index)
    for h in horizons:
        df[f"forward_ret_{h}d"] = forward_return(returns, h)
        df[f"mfe_{h}d"] = forward_mfe(returns, h)
        df[f"mae_{h}d"] = forward_mae(returns, h)
    return df
