"""Sprint R&D Edge Privé R2 — Pairs trading single-name sectorielles.

Différent de SPY-QQQ pair (testé fail) : single-name intra-sector less arbitré.

Pairs pré-déclarés frozen (3, pas 15) :
  - JPM-BAC (banques majeures)
  - XOP-CVX (énergie : E&P vs intégré)
  - MA-V (paiements)

Règle frozen :
  - Z-score 60d
  - Entry |z|>2.0
  - Exit |z|<0.5
  - Beta-neutral sizing (50/50 dollar exposure)
  - 10 bps round-trip × 2 legs

Critère PASS : Sharpe net > 0.7 + market-neutral confirmé (β SPY ≈ 0) + 2+/3 pairs PASS
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_F2 = backend_dir / "data" / "f2_daily"

PAIRS = [
    ("JPM", "BAC", "Banks"),
    ("XOP", "CVX", "Energy E&P vs integrated"),
    ("MA", "V", "Payments"),
]
LOOKBACK = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
COST_BPS_RT = 10.0  # per leg
START = "2019-06-01"
END = "2025-11-30"


def fetch_ticker(t: str) -> pd.Series:
    df = yf.download(t, start=START, end=END, interval="1d",
                     progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()


def compute_pair_zscore(p1: pd.Series, p2: pd.Series, lookback: int) -> pd.Series:
    """Log-spread z-score (cointegration-style mean-reversion).

    spread = log(p1) - log(p2), rolling z-score over `lookback` days.
    """
    log_spread = np.log(p1) - np.log(p2)
    rolling_mean = log_spread.rolling(lookback).mean()
    rolling_std = log_spread.rolling(lookback).std()
    z = (log_spread - rolling_mean) / rolling_std.replace(0, np.nan)
    return z.dropna()


def run_pair(t1: str, t2: str, label: str, spy: pd.Series) -> dict:
    p1 = fetch_ticker(t1)
    p2 = fetch_ticker(t2)
    common = p1.index.intersection(p2.index).intersection(spy.index)
    p1, p2, spy_aligned = p1.loc[common], p2.loc[common], spy.loc[common]
    n = len(common)
    print(f"\n=== Pair {t1}-{t2} ({label}) ===")
    print(f"  Data : {n} days, {common.min().date()} → {common.max().date()}")

    z = compute_pair_zscore(p1, p2, LOOKBACK)
    common_z = z.index
    p1, p2 = p1.loc[common_z], p2.loc[common_z]
    spy_aligned = spy_aligned.loc[common_z]
    print(f"  Z-score : mean={z.mean():.3f}, std={z.std():.3f}, "
          f"p10={z.quantile(0.1):.2f}, p90={z.quantile(0.9):.2f}")

    # Generate position : 1 (long spread = long p1/short p2) when z<-2, -1 (short spread) when z>+2
    position = pd.Series(0.0, index=z.index)
    cur = 0
    for i, val in enumerate(z.values):
        if cur == 0:
            if val < -Z_ENTRY:
                cur = 1  # long spread
            elif val > Z_ENTRY:
                cur = -1  # short spread
        else:
            if abs(val) < Z_EXIT:
                cur = 0
        position.iloc[i] = cur

    # Compute spread return (long p1 + short p2 = log_p1_ret - log_p2_ret approx)
    p1_ret = p1.pct_change().fillna(0)
    p2_ret = p2.pct_change().fillna(0)
    spread_ret = p1_ret - p2_ret  # 50/50 dollar exposure approximation

    daily_strat = position.shift(1).fillna(0) * spread_ret
    pos_change = position.diff().abs().fillna(0)
    # Cost : per position change, 2 legs × cost_bps
    cost_per_change = 2 * (COST_BPS_RT / 10000.0)
    cost = pos_change * cost_per_change
    daily_strat_net = daily_strat - cost

    # Stats
    n_trades = int((pos_change != 0).sum() / 2)
    pct_in = float((position != 0).mean() * 100)
    eq = (1 + daily_strat_net).cumprod()
    days = (eq.index[-1] - eq.index[0]).days
    years = days / 365.25
    cagr = eq.iloc[-1] ** (1/years) - 1 if years > 0 else 0
    sharpe = daily_strat_net.mean() / daily_strat_net.std() * np.sqrt(252) if daily_strat_net.std() > 0 else 0
    rm = eq.expanding().max()
    dd = float((eq / rm - 1).min())
    calmar = cagr / abs(dd) if dd < 0 else 0

    # Beta vs SPY (market-neutrality check)
    spy_ret = spy_aligned.pct_change().fillna(0)
    if daily_strat_net.std() > 0 and spy_ret.std() > 0:
        beta = np.cov(daily_strat_net, spy_ret)[0, 1] / spy_ret.var()
    else:
        beta = 0.0

    print(f"  Strategy : Sharpe={sharpe:+.3f}  CAGR={cagr*100:+.2f}%  DD={dd*100:+.1f}%  "
          f"Calmar={calmar:+.2f}  β SPY={beta:+.3f}")
    print(f"  Trades : {n_trades} round-trips, {pct_in:.1f}% time in market")

    # Sub-sample
    split_date = pd.Timestamp("2022-06-01")
    sub1 = daily_strat_net.loc[daily_strat_net.index[0]:split_date].dropna()
    sub2 = daily_strat_net.loc[split_date:daily_strat_net.index[-1]].dropna()
    sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
    sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
    print(f"  Sub-sample : 2019-2022 Sharpe={sh1:+.2f} | 2022-2025 Sharpe={sh2:+.2f} | "
          f"ΔSharpe={sh2-sh1:+.2f}")

    # Gate
    pass_sharpe = sharpe >= 0.7
    market_neutral = abs(beta) < 0.15
    verdict = "PASS" if (pass_sharpe and market_neutral) else \
              ("KILL" if sharpe < 0.3 else "MARGINAL")
    print(f"\n  Gate :")
    print(f"    Sharpe ≥ 0.7 : {'PASS' if pass_sharpe else 'FAIL'} (got {sharpe:.2f})")
    print(f"    Market-neutral |β| < 0.15 : {'PASS' if market_neutral else 'FAIL'} (got {beta:+.3f})")
    print(f"    → {verdict}")

    return {
        "pair": f"{t1}-{t2}",
        "label": label,
        "Sharpe": sharpe,
        "CAGR_pct": cagr * 100,
        "max_DD_pct": dd * 100,
        "Calmar": calmar,
        "beta_SPY": beta,
        "n_trades": n_trades,
        "pct_in_market": pct_in,
        "delta_subsample": sh2 - sh1,
        "verdict": verdict,
    }


def main() -> None:
    print("=" * 100)
    print("Sprint R&D Edge Privé R2 — Pairs trading single-name sectorielles")
    print("=" * 100)

    spy_df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
    spy_df["date"] = pd.to_datetime(spy_df["date"])
    spy = spy_df.set_index("date")["Close"].sort_index()

    print(f"\nFrozen : lookback={LOOKBACK}d, entry |z|>{Z_ENTRY}, exit |z|<{Z_EXIT}, "
          f"cost {COST_BPS_RT} bps RT × 2 legs")

    all_results = []
    for t1, t2, label in PAIRS:
        r = run_pair(t1, t2, label, spy)
        all_results.append(r)

    # Cross-pair summary
    print()
    print("=" * 100)
    print("Cross-pair summary R2")
    print("=" * 100)
    print(f"{'Pair':<12} {'Label':<28} {'Sharpe':>7} {'Calmar':>7} {'β SPY':>7} {'Verdict':>10}")
    n_pass = 0
    for r in all_results:
        print(f"{r['pair']:<12} {r['label']:<28} {r['Sharpe']:>+7.2f} {r['Calmar']:>+7.2f} "
              f"{r['beta_SPY']:>+7.3f} {r['verdict']:>10}")
        if r['verdict'] == "PASS":
            n_pass += 1
    print(f"\n  {n_pass}/3 PASS")

    # Save
    out_dir = backend_dir / "results" / "rd_edge_r2_pairs_sectorielles"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_results).to_parquet(out_dir / "results.parquet", index=False)
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
