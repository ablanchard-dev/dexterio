"""F2 ML metalabel overlay — D step per plan v4.0 §9.1 debloqué.

Pipeline :
  1. Load 2019-2025 corpus (9 ETFs + VIX).
  2. Run momentum J&T (best non-overlay per C reality check : 6.5y Sharpe 0.73).
  3. Compute daily strategy returns.
  4. Build features (VIX level/change, SPY momentum, day_of_week, strat own
     momentum).
  5. Train classifier 60/40 temporal split, threshold p_win >= 0.4.
  6. Report unfiltered vs filtered Sharpe/CAGR/maxDD on test set.

Hypothèse : si VIX overlay binaire (fertile 15-25) détruit le long-term edge
(§C : 2.79→0.31), un classifier ML multi-feature apprend peut-être une règle
nuancée qui preserve le signal.

Caveat honnête : si metalabel = vanity improvement (test_acc ~55%, mais filter
réduit sample size → high variance), reporter sans survendre.

Usage : python backend/scripts/f2/run_f2_metalabel.py
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
from engines.portfolio.metalabeling import build_features, train_metalabel

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


def main() -> None:
    prices = load_prices()
    vix = load_vix()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {len(TICKERS)} tickers)")

    # 1. Run momentum J&T strategy (best non-overlay from C).
    alloc = PortfolioAllocator(TICKERS)
    equity, metrics, _ = run_backtest(
        prices, alloc, method="momentum",
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        jt_lookback=12, jt_skip=1, jt_top_n=3,
    )
    print()
    print(f"Momentum J&T unfiltered : Sharpe={metrics.sharpe_daily_annualized:.3f}, "
          f"CAGR={metrics.cagr*100:.2f}%, maxDD={metrics.max_drawdown*100:.1f}%")

    # 2. Strategy daily returns.
    strat_returns = equity.pct_change().dropna()
    print(f"Strategy returns : n={len(strat_returns)}, "
          f"mean={strat_returns.mean()*100:.4f}%, std={strat_returns.std()*100:.3f}%")

    # 3. Build features + train.
    spy = prices["SPY"]
    features = build_features(strat_returns, vix, spy)
    print(f"Features : {len(features)} rows, {len(features.columns)} cols "
          f"({list(features.columns)})")
    print()

    clf, result = train_metalabel(
        features, strat_returns,
        train_fraction=0.6,
        threshold=0.0,
        model="random_forest",
    )

    # 4. Report.
    print("=" * 70)
    print(f"  n_train                  : {result.n_train}")
    print(f"  n_test                   : {result.n_test}")
    print(f"  train accuracy           : {result.train_accuracy:.3f}")
    print(f"  test accuracy            : {result.test_accuracy:.3f}")
    print(f"  baseline (always predict 1): {(strat_returns > 0).mean():.3f}")
    print(f"  n_skipped on test        : {result.n_skipped_test} / {result.n_test} "
          f"({result.n_skipped_test/result.n_test*100:.1f}%)")
    print()
    print(f"{'metric':<20} {'unfiltered':>12} {'filtered':>12} {'delta':>10}")
    print("-" * 56)
    print(f"{'Sharpe (ann)':<20} {result.sharpe_unfiltered:>12.3f} "
          f"{result.sharpe_filtered:>12.3f} "
          f"{result.sharpe_filtered - result.sharpe_unfiltered:>+10.3f}")
    print(f"{'CAGR':<20} {result.cagr_unfiltered*100:>11.2f}% "
          f"{result.cagr_filtered*100:>11.2f}% "
          f"{(result.cagr_filtered - result.cagr_unfiltered)*100:>+9.2f}%")
    print(f"{'Max DD':<20} {result.max_dd_unfiltered*100:>11.1f}% "
          f"{result.max_dd_filtered*100:>11.1f}% "
          f"{(result.max_dd_filtered - result.max_dd_unfiltered)*100:>+9.1f}%")
    print()
    print("Feature importances (top) :")
    fi = sorted(result.feature_importances.items(), key=lambda x: -x[1])
    for feat, imp in fi:
        print(f"  {feat:<20} {imp:.4f}")
    print()
    test_start = features.index[int(len(features) * 0.6)]
    print(f"Test period : {test_start.date()} → {features.index[-1].date()}")

    # Gate per plan v4.0 §9.1.
    delta = result.sharpe_filtered - result.sharpe_unfiltered
    pass_gate = delta >= 0.2
    print()
    print(f"Gate D (Sharpe_filtered ≥ Sharpe_unfiltered + 0.2) : "
          f"{'PASS' if pass_gate else 'FAIL'} (delta={delta:+.3f})")


if __name__ == "__main__":
    main()
