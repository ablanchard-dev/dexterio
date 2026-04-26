"""F2 VIX fertile regime stress — 6.5y validation per plan v4.0 §0.4-bis.

2y run (jun 2023 → nov 2025) montrait Sharpe 2.79 dans regime fertile (VIX
15-25, n=300). Question : ce subset tient-il sur 6.5 ans ou disparaît-il
dans un corpus qui inclut COVID (Mar 2020) + 2022 bear + 2024 calme ?

Méthode :
  1. Run momentum J&T (pas d'overlay, best non-overlay 6.5y).
  2. Split les daily returns par regime VIX (low <15, fertile 15-25,
     elevated 25-30, panic >=30).
  3. Reporter per-regime Sharpe + n + contrib total.
  4. Comparer au 2y baseline : si fertile Sharpe >= 1.5 sur 6.5y, confirme
     edge regime-conditional. Sinon, bull artifact répliqué sur fertile.

Usage : python backend/scripts/f2/run_f2_fertile_longterm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.portfolio.allocator import PortfolioAllocator
from engines.portfolio.backtester import run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "GLD", "TLT", "FXI"]


def load_prices():
    frames = []
    for t in TICKERS:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def load_vix():
    df = pd.read_parquet(DATA_DIR / "VIX_1d.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["Close"].rename("VIX")


def regime_split(returns: pd.Series, vix: pd.Series) -> dict:
    aligned_idx = returns.index.intersection(vix.index)
    r = returns.loc[aligned_idx]
    vx = vix.loc[aligned_idx].shift(1)  # prior-day VIX (actionable)
    splits = {
        "low_vol (VIX<15)":    (vx < 15),
        "fertile (15-25)":     ((vx >= 15) & (vx < 25)),
        "elevated (25-30)":    ((vx >= 25) & (vx < 30)),
        "panic (>=30)":        (vx >= 30),
    }
    out = {}
    for name, mask in splits.items():
        rm = r[mask].dropna()
        if len(rm) < 5:
            out[name] = {"n": len(rm), "sharpe": 0, "mean": 0, "total": 0}
            continue
        sharpe = float(rm.mean() / rm.std() * np.sqrt(252)) if rm.std() > 0 else 0
        out[name] = {
            "n": int(len(rm)),
            "mean_daily_bps": float(rm.mean() * 10000),
            "sharpe_ann": sharpe,
            "total_contrib_pct": float(rm.sum() * 100),
            "pct_of_days": float(len(rm) / len(r) * 100),
        }
    return out


def main() -> None:
    prices = load_prices()
    vix = load_vix()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days)")

    alloc = PortfolioAllocator(TICKERS)
    equity, metrics, _ = run_backtest(
        prices, alloc, method="momentum",
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        jt_lookback=12, jt_skip=1, jt_top_n=3,
    )
    returns = equity.pct_change().dropna()
    print(f"Momentum J&T 6.5y unfiltered : Sharpe={metrics.sharpe_daily_annualized:.3f}, "
          f"CAGR={metrics.cagr*100:.2f}%, maxDD={metrics.max_drawdown*100:.1f}%")
    print()

    splits = regime_split(returns, vix)
    print(f"{'regime':<22} {'n':>5} {'%days':>7} {'mean_bps':>9} {'Sharpe':>8} {'contrib%':>10}")
    print("-" * 75)
    for regime, s in splits.items():
        if s["n"] < 5:
            print(f"  {regime:<20} n={s['n']:<3} (insufficient)")
            continue
        print(f"  {regime:<20} {s['n']:>5} {s['pct_of_days']:>6.1f}% "
              f"{s['mean_daily_bps']:>9.1f} {s['sharpe_ann']:>8.2f} "
              f"{s['total_contrib_pct']:>9.1f}%")

    # Compare vs 2y baseline (run_f2_smoke_v2.py reported : fertile Sharpe 2.79 n=300)
    print()
    print("=== Compare vs 2y baseline (jun 2023 → nov 2025) ===")
    mask_2y = returns.index >= pd.Timestamp("2023-06-01")
    splits_2y = regime_split(returns[mask_2y], vix)
    for regime in splits.keys():
        s65 = splits[regime]
        s2 = splits_2y[regime]
        if s65["n"] < 5 or s2["n"] < 5:
            continue
        print(f"  {regime:<22} 6.5y Sharpe={s65['sharpe_ann']:>5.2f} (n={s65['n']}) "
              f"| 2y Sharpe={s2['sharpe_ann']:>5.2f} (n={s2['n']}) "
              f"| Δ={s65['sharpe_ann']-s2['sharpe_ann']:+.2f}")

    # Gate : fertile on 6.5y Sharpe >= 1.5 (halfway between baseline 0.73 and 2y fertile 2.79)
    fertile_65 = splits["fertile (15-25)"]["sharpe_ann"]
    print()
    print(f"Gate fertile regime 6.5y Sharpe >= 1.5 : "
          f"{'PASS' if fertile_65 >= 1.5 else 'FAIL'} (got {fertile_65:.2f})")

    # Sub-regime dates : when did fertile mostly fall ?
    print()
    print("=== Fertile regime temporal distribution (by year) ===")
    aligned_idx = returns.index.intersection(vix.index)
    vx_prior = vix.loc[aligned_idx].shift(1)
    fertile_mask = (vx_prior >= 15) & (vx_prior < 25)
    fertile_days = returns.loc[aligned_idx][fertile_mask]
    for year in range(2020, 2026):
        days_y = fertile_days[fertile_days.index.year == year]
        if len(days_y) < 5:
            continue
        sh = float(days_y.mean() / days_y.std() * np.sqrt(252)) if days_y.std() > 0 else 0
        print(f"  {year}: n={len(days_y):>4}  Sharpe={sh:>5.2f}  "
              f"total_contrib={days_y.sum()*100:>6.2f}%")


if __name__ == "__main__":
    main()
