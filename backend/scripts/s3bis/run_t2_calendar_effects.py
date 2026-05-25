"""S+3-bis T2 — Calendar effects per-asset (turn-of-month + day-of-week + FOMC drift).

Idée corpus : académique classique (Cross 1973 weekend, French 1980 day-of-week,
Lakonishok 1988 turn-of-month, Wachtel 1942) + référencé 9Y3yaoi9rUQ Project 1.

Assets pré-déclarés : SPY + QQQ + GLD + BTC daily.
4 verdicts indépendants per asset, benchmark per asset.

Effets pré-déclarés (frozen, sans cherry-pick) :
  - Turn-of-month : long last 5 trading days month + first 3 days, cash sinon
  - Day-of-week : test "long Monday vs Friday" hypothèse fixe (pas best day)
  - FOMC drift : long 5 days pre-FOMC + flat post (FOMC dates hardcoded Wikipedia)

Verdict per asset :
  - PASS : Sharpe > 0.6 + beat asset buy-hold + permutation p<0.10 si borderline
  - KILL : Sharpe < 0.3 OR worse than buy-hold

Cross-asset : 2+/4 PASS = robust cross-asset edge ; 0-1/4 = pas universel.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# FOMC meeting dates 2019-2025 (source : Wikipedia + federalreserve.gov public list, frozen)
FOMC_DATES = [
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29",
]

DATA_F2 = backend_dir / "data" / "f2_daily"
DATA_CRYPTO = backend_dir / "data" / "crypto"


def load_asset_prices(asset: str) -> pd.Series:
    """Load daily close prices for asset. Returns Series indexed by date."""
    if asset == "SPY":
        df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "QQQ":
        df = pd.read_parquet(DATA_F2 / "QQQ_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "GLD":
        df = pd.read_parquet(DATA_F2 / "GLD_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "BTC":
        df = pd.read_parquet(DATA_CRYPTO / "BTCUSDT_spot_1d_6.5y.parquet")
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.tz_localize(None).dt.normalize()
        return df.set_index("date")["close"].sort_index()
    raise ValueError(f"Unknown asset {asset}")


def turn_of_month_signal(prices: pd.Series) -> pd.Series:
    """Long last 5 trading days of month + first 3 days, cash otherwise."""
    dates = prices.index
    # Group by year-month
    months = dates.to_period("M")
    signal = pd.Series(0.0, index=dates)
    for period in months.unique():
        mask = months == period
        idxs = np.where(mask)[0]
        if len(idxs) < 6:
            continue
        # Last 5 trading days of month
        signal.iloc[idxs[-5:]] = 1.0
        # First 3 trading days of next month (handled by next iter or first 3 of THIS month)
    # First 3 trading days of each month
    for period in months.unique():
        mask = months == period
        idxs = np.where(mask)[0]
        if len(idxs) >= 3:
            signal.iloc[idxs[:3]] = 1.0
    return signal


def day_of_week_signal(prices: pd.Series, day: int = 0) -> pd.Series:
    """Long on `day` (0=Mon, 4=Fri), cash otherwise."""
    return pd.Series((prices.index.dayofweek == day).astype(float),
                      index=prices.index)


def fomc_drift_signal(prices: pd.Series, days_pre: int = 5) -> pd.Series:
    """Long 5 days pre-FOMC, flat on/post FOMC."""
    fomc_dates = pd.to_datetime(FOMC_DATES)
    signal = pd.Series(0.0, index=prices.index)
    for fdate in fomc_dates:
        # Find trading days within [fdate - 5 trading days, fdate - 1]
        prior_idx = prices.index[prices.index < fdate]
        if len(prior_idx) >= days_pre:
            window = prior_idx[-days_pre:]
            signal.loc[window] = 1.0
    return signal


def apply_signal(prices: pd.Series, signal: pd.Series,
                  cost_bps: float = 5.0) -> pd.Series:
    """Apply binary signal to asset returns. Cost on signal change."""
    rets = prices.pct_change().fillna(0)
    pos = signal.shift(1).fillna(0)  # use yesterday's signal for today's return
    daily_ret = pos * rets
    # Turnover cost
    turnover = signal.diff().abs().fillna(0)
    cost = turnover * (cost_bps / 10000.0)
    return daily_ret - cost


def compute_metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    rets = rets[rets.index >= rets.first_valid_index()] if rets.first_valid_index() else rets
    if len(rets) < 30:
        return {"label": label, "valid": False}
    eq = (1 + rets).cumprod()
    final_ret = eq.iloc[-1] - 1
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd = float((eq / rm - 1).min())
    calmar = cagr / abs(dd) if dd < 0 else 0
    return {
        "label": label, "valid": True, "n_days": len(rets),
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": float(sharpe),
        "max_DD_pct": dd * 100,
        "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
        "pct_time_in": float((rets != 0).mean() * 100),
    }


def main() -> None:
    assets = ["SPY", "QQQ", "GLD", "BTC"]
    effects = ["turn_of_month", "day_of_week_monday", "day_of_week_friday", "fomc_drift"]

    print("=" * 110)
    print("S+3-bis T2 — Calendar effects per-asset (4 effects × 4 assets = 16 verdicts indépendants)")
    print("=" * 110)

    all_results = []
    for asset in assets:
        prices = load_asset_prices(asset)
        bh_rets = prices.pct_change().fillna(0)
        bh_metrics = compute_metrics(bh_rets, f"{asset} buy-hold")
        print(f"\n=== {asset} (n={len(prices)}, {prices.index.min().date()} → "
              f"{prices.index.max().date()}) ===")
        print(f"  Buy-hold ref : Sharpe={bh_metrics['Sharpe_ann']:+.3f} "
              f"CAGR={bh_metrics['CAGR_pct']:+.2f}% maxDD={bh_metrics['max_DD_pct']:+.1f}%")

        for effect_name in effects:
            if effect_name == "turn_of_month":
                signal = turn_of_month_signal(prices)
            elif effect_name == "day_of_week_monday":
                signal = day_of_week_signal(prices, day=0)
            elif effect_name == "day_of_week_friday":
                signal = day_of_week_signal(prices, day=4)
            elif effect_name == "fomc_drift":
                signal = fomc_drift_signal(prices, days_pre=5)
            rets = apply_signal(prices, signal)
            m = compute_metrics(rets, f"{asset} {effect_name}")
            beat_bh = m["Sharpe_ann"] > bh_metrics["Sharpe_ann"]
            pass_gate = m["Sharpe_ann"] > 0.6 and beat_bh
            kill = m["Sharpe_ann"] < 0.3
            verdict = "PASS" if pass_gate else ("KILL" if kill else "MARGINAL")
            print(f"    {effect_name:<25} Sharpe={m['Sharpe_ann']:+.3f} "
                  f"CAGR={m['CAGR_pct']:+.2f}% DD={m['max_DD_pct']:+.1f}% "
                  f"%in={m['pct_time_in']:.0f}% beat_bh={beat_bh}  → {verdict}")
            all_results.append({
                "asset": asset, "effect": effect_name,
                "Sharpe": m["Sharpe_ann"], "CAGR_pct": m["CAGR_pct"],
                "max_DD_pct": m["max_DD_pct"], "pct_time_in": m["pct_time_in"],
                "bh_Sharpe": bh_metrics["Sharpe_ann"], "beat_bh": beat_bh,
                "verdict": verdict,
            })

    # Cross-asset summary per effect
    print()
    print("=" * 110)
    print("Cross-asset summary per effect (PASS = Sharpe > 0.6 ET beat buy-hold)")
    print("=" * 110)
    df = pd.DataFrame(all_results)
    for effect_name in effects:
        sub = df[df["effect"] == effect_name]
        n_pass = (sub["verdict"] == "PASS").sum()
        n_kill = (sub["verdict"] == "KILL").sum()
        n_marg = (sub["verdict"] == "MARGINAL").sum()
        sharpes = sub["Sharpe"].tolist()
        verdict_global = ("ROBUST" if n_pass >= 2 else
                          ("MARGINAL" if n_pass >= 1 else "DEAD"))
        print(f"  {effect_name:<25} PASS={n_pass}/4  KILL={n_kill}  MARGINAL={n_marg}  "
              f"Sharpes: {sharpes}  → {verdict_global}")

    # Save
    out_dir = backend_dir / "results" / "s3bis_t2_calendar"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "results.parquet", index=False)
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
