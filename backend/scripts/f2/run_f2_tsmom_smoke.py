"""F2 Time-Series Momentum (TSMOM) smoke 6.5y — Priority #1 plan v4.0 J1.

TSMOM per-asset (Moskowitz/Ooi/Pedersen 2012) sur SPY/QQQ/GLD/TLT.
Différent du J&T cross-sectional (déjà tué F2 v1) — ici signal absolu
per-asset (long si r_252 > 0 sinon cash), pas ranking relatif.

Universe : SPY (SP500), QQQ (Nasdaq), GLD (Gold), TLT (Treasury bonds long).
4 actifs cross-asset = aligne vision user (SP500 + Nasdaq + Gold + diversification).

Hypothèse : Sharpe net 6.5y > 0.8, max DD < 20%.
Kill rule (J3) : Sharpe < 0.6 → ARCHIVE, pas d'iteration lookback.

Usage : python backend/scripts/f2/run_f2_tsmom_smoke.py
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
from engines.portfolio.backtester import buy_and_hold, run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "GLD", "TLT"]


def load_prices(tickers):
    frames = []
    for t in tickers:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def sharpe_ann(r):
    r = r.dropna()
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def main() -> None:
    prices = load_prices(TICKERS)
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {len(TICKERS)} assets : {TICKERS})")
    print()

    # SPY buy-and-hold reference
    bh = buy_and_hold(prices, "SPY")
    bh_ret = bh.pct_change().dropna()
    print(f"REFERENCE — SPY buy-and-hold 6.5y :")
    print(f"  return    : {(bh.iloc[-1]/bh.iloc[0]-1)*100:>6.1f}%")
    print(f"  Sharpe    : {sharpe_ann(bh_ret):>6.2f}")
    print(f"  max DD    : {((bh / bh.expanding().max()) - 1).min() * 100:>6.1f}%")
    print()

    # TSMOM portfolio (12-month lookback, monthly rebalance)
    alloc = PortfolioAllocator(TICKERS)
    print(f"TSMOM portfolio (lookback=252d, rebalance=21d, vol_target=10%, tc=10bps) :")
    eq, m, hist = run_backtest(
        prices, alloc, method="tsmom",
        overlays=["vol_target"],
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        target_annual_vol=0.10,
        tsmom_lookback_days=252,
    )
    print(f"  return    : {m.total_return*100:>6.1f}%")
    print(f"  CAGR      : {m.cagr*100:>6.2f}%")
    print(f"  Sharpe    : {m.sharpe_daily_annualized:>6.2f}")
    print(f"  Martin    : {m.martin_ratio:>6.2f}")
    print(f"  max DD    : {m.max_drawdown*100:>6.1f}%")
    print(f"  vol_ann   : {m.volatility_annualized*100:>6.1f}%")
    print(f"  cash_avg  : {m.cash_avg*100:>6.1f}%")
    print(f"  n_rebal   : {m.n_rebalances}")
    print()

    # Per-asset positioning analysis : how often each ticker is long
    long_counts = {t: 0 for t in TICKERS}
    for h in hist:
        for t, w in h.weights.items():
            if w > 0:
                long_counts[t] += 1
    n_total = len(hist)
    print("Per-asset long positioning (% of rebalances long) :")
    for t in TICKERS:
        pct = long_counts[t] / n_total * 100 if n_total > 0 else 0
        print(f"  {t:<5} : {long_counts[t]:>3}/{n_total} = {pct:>5.1f}%")
    print()

    # No-overlay version (pure TSMOM equal-weight long, no vol-target, no TC) for diagnostic
    print(f"TSMOM diagnostic (no vol_target, no TC — pure signal performance) :")
    eq_pure, m_pure, _ = run_backtest(
        prices, alloc, method="tsmom",
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=0.0,
        tsmom_lookback_days=252,
    )
    print(f"  Sharpe    : {m_pure.sharpe_daily_annualized:>6.2f}")
    print(f"  CAGR      : {m_pure.cagr*100:>6.2f}%")
    print(f"  max DD    : {m_pure.max_drawdown*100:>6.1f}%")
    print()

    # Gate kill rules (J3)
    sharpe = m.sharpe_daily_annualized
    pass_sharpe = sharpe >= 0.8
    pass_kill_rule = sharpe >= 0.6
    print("=== Kill rules pré-écrites (plan J3) ===")
    print(f"  Sharpe >= 0.8 (PASS bar)  : {'PASS' if pass_sharpe else 'FAIL'} (got {sharpe:.2f})")
    print(f"  Sharpe >= 0.6 (kill rule) : {'OK' if pass_kill_rule else 'KILL'} (got {sharpe:.2f})")
    print(f"  max DD < 20%              : {'PASS' if abs(m.max_drawdown) < 0.20 else 'FAIL'} (got {m.max_drawdown*100:.1f}%)")
    print()
    print("Next : per-asset Sharpe + bar permutation (J2)")


if __name__ == "__main__":
    main()
