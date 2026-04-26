"""F2 TSMOM bar permutation test — Priority #1 plan v4.0 J2.

Test : real TSMOM Sharpe vs random permutations of daily returns per ticker.
Bar-shuffle destroys serial structure → if TSMOM has real time-series persistence
edge, real Sharpe should beat ~95% of permutations.

Method (500 iter, seed=42) :
  1. Real TSMOM 6.5y → Sharpe_real
  2. For each iter : shuffle daily returns per ticker indep, rebuild prices,
     recompute TSMOM Sharpe
  3. p-value = fraction shuffled Sharpe >= real
  4. PASS if p < 0.05 (kill rule plan : p > 0.10 → ARCHIVE)

Usage : python backend/scripts/f2/run_f2_tsmom_permutation.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.portfolio.allocator import PortfolioAllocator
from engines.portfolio.backtester import run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "GLD", "TLT"]
N_PERMUTATIONS = 500
SEED = 42


def load_prices():
    frames = []
    for t in TICKERS:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def tsmom_sharpe(prices: pd.DataFrame) -> float:
    alloc = PortfolioAllocator(TICKERS)
    eq, m, _ = run_backtest(
        prices, alloc, method="tsmom",
        overlays=["vol_target"],
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        target_annual_vol=0.10,
        tsmom_lookback_days=252,
    )
    return m.sharpe_daily_annualized


def permute_prices(prices: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    new_prices = pd.DataFrame(index=prices.index, columns=prices.columns)
    for t in prices.columns:
        returns = prices[t].pct_change().dropna().values
        shuffled = rng.permutation(returns)
        first_price = prices[t].iloc[0]
        cumulative = np.concatenate([[first_price],
                                      first_price * np.cumprod(1 + shuffled)])
        if len(cumulative) < len(prices):
            cumulative = np.concatenate([cumulative,
                                          np.full(len(prices) - len(cumulative),
                                                  cumulative[-1])])
        new_prices[t] = cumulative[:len(prices)]
    return new_prices.astype(float)


def main() -> None:
    prices = load_prices()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {TICKERS})")

    sharpe_real = tsmom_sharpe(prices)
    print(f"Real TSMOM Sharpe (6.5y, vol_target 10%, tc 10bps) : {sharpe_real:.4f}")
    print(f"Running {N_PERMUTATIONS} permutations (seed={SEED})...")

    rng = np.random.default_rng(SEED)
    shuffled_sharpes = []
    t0 = time.time()
    for i in range(N_PERMUTATIONS):
        perm = permute_prices(prices, rng)
        try:
            s = tsmom_sharpe(perm)
            shuffled_sharpes.append(s)
        except Exception:
            shuffled_sharpes.append(0.0)
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta_min = (N_PERMUTATIONS - i - 1) / rate / 60
            mean_so_far = np.mean(shuffled_sharpes)
            p_so_far = np.mean([s >= sharpe_real for s in shuffled_sharpes])
            print(f"  iter {i+1:>4} / {N_PERMUTATIONS} | rate {rate:.1f}/s | "
                  f"ETA {eta_min:.1f}min | mean_shuffled={mean_so_far:.3f} | "
                  f"p_so_far={p_so_far:.4f}")

    elapsed_total = time.time() - t0
    mean_shuffled = float(np.mean(shuffled_sharpes))
    std_shuffled = float(np.std(shuffled_sharpes))
    p_value = float(np.mean([s >= sharpe_real for s in shuffled_sharpes]))
    z_score = (sharpe_real - mean_shuffled) / std_shuffled if std_shuffled > 0 else 0
    p95 = float(np.percentile(shuffled_sharpes, 95))
    p99 = float(np.percentile(shuffled_sharpes, 99))

    print()
    print(f"=== Permutation results ({N_PERMUTATIONS} iter, {elapsed_total/60:.1f} min) ===")
    print(f"  real Sharpe              : {sharpe_real:.4f}")
    print(f"  shuffled mean Sharpe     : {mean_shuffled:.4f}")
    print(f"  shuffled std Sharpe      : {std_shuffled:.4f}")
    print(f"  shuffled p95 / p99       : {p95:.3f} / {p99:.3f}")
    print(f"  z-score                  : {z_score:.3f}")
    print(f"  p-value (one-sided)      : {p_value:.4f}")
    print()
    print(f"  GATE p < 0.05 (PASS bar) : {'PASS' if p_value < 0.05 else 'FAIL'}")
    print(f"  KILL p > 0.10 (archive)  : {'KILL' if p_value > 0.10 else 'OK'}")


if __name__ == "__main__":
    main()
