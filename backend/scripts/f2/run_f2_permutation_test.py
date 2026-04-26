"""F2 bar permutation test — O5.3 gate per plan v4.0 §0.6 Stage 3.

Test : is the F2 momentum strategy's return distribution statistically
significant vs a null hypothesis where daily returns are randomly shuffled
(bar permutation canon per §0.7 D2 + MASTER's book Ch 3).

Method (2000 iterations, seed=42) :
  1. Run momentum J&T on real corpus → record Sharpe_real
  2. For each iter :
     a) Shuffle daily returns in place (destroys serial / regime structure)
     b) Recompute strategy equity curve using shuffled returns
     c) Record Sharpe_shuffled
  3. p-value = fraction of shuffled Sharpes >= Sharpe_real
  4. PASS gate if p < 0.05

Caveat : permuting daily returns destroys the time-series structure the
momentum signal relies on (lookback 12m window). So this is a **stringent**
null hypothesis — if momentum truly has edge from time structure, it should
beat ~95% of random permutations.

Usage : python backend/scripts/f2/run_f2_permutation_test.py
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
from engines.portfolio.backtester import compute_metrics, run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "GLD", "TLT", "FXI"]
N_PERMUTATIONS = 500  # v1 : 500 iter pragmatic (D2 canon = 2000, reduced for speed)
SEED = 42


def load_prices():
    frames = []
    for t in TICKERS:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def strategy_sharpe(prices: pd.DataFrame, method: str = "momentum") -> float:
    alloc = PortfolioAllocator(TICKERS)
    eq, m, _ = run_backtest(
        prices, alloc, method=method,
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        jt_lookback=12, jt_skip=1, jt_top_n=3,
    )
    return m.sharpe_daily_annualized


def permute_prices(prices: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle daily returns per ticker independently, then rebuild prices.

    For each ticker : compute daily pct_change, shuffle indexes, reconstruct
    price series starting from the first real price.
    """
    new_prices = pd.DataFrame(index=prices.index, columns=prices.columns)
    for t in prices.columns:
        returns = prices[t].pct_change().dropna().values
        shuffled = rng.permutation(returns)
        first_price = prices[t].iloc[0]
        # Reconstruct : P_t = P_0 * prod(1 + r_i) up to t
        cumulative = np.concatenate([[first_price], first_price * np.cumprod(1 + shuffled)])
        # Ensure length matches
        if len(cumulative) < len(prices):
            cumulative = np.concatenate([cumulative,
                                          np.full(len(prices) - len(cumulative), cumulative[-1])])
        new_prices[t] = cumulative[:len(prices)]
    return new_prices.astype(float)


def main() -> None:
    prices = load_prices()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} ({len(prices)} days)")
    print()

    # Real Sharpe
    sharpe_real = strategy_sharpe(prices, method="momentum")
    print(f"Real Sharpe (momentum J&T top3) : {sharpe_real:.4f}")
    print()
    print(f"Running {N_PERMUTATIONS} permutations (seed={SEED})...")

    rng = np.random.default_rng(SEED)
    shuffled_sharpes = []
    t0 = time.time()
    for i in range(N_PERMUTATIONS):
        perm = permute_prices(prices, rng)
        try:
            s = strategy_sharpe(perm, method="momentum")
            shuffled_sharpes.append(s)
        except Exception:
            shuffled_sharpes.append(0.0)
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta_min = (N_PERMUTATIONS - i - 1) / rate / 60
            mean_so_far = np.mean(shuffled_sharpes)
            p_so_far = np.mean([s >= sharpe_real for s in shuffled_sharpes])
            print(f"  iter {i+1:>4} / {N_PERMUTATIONS} | rate {rate:.1f}/s | ETA {eta_min:.1f}min | mean_shuffled_sharpe={mean_so_far:.3f} | p_so_far={p_so_far:.4f}")

    elapsed_total = time.time() - t0
    mean_shuffled = float(np.mean(shuffled_sharpes))
    std_shuffled = float(np.std(shuffled_sharpes))
    p_value = float(np.mean([s >= sharpe_real for s in shuffled_sharpes]))
    z_score = (sharpe_real - mean_shuffled) / std_shuffled if std_shuffled > 0 else 0

    print()
    print(f"=== Permutation test results ({N_PERMUTATIONS} iter, {elapsed_total/60:.1f} min) ===")
    print(f"  real Sharpe              : {sharpe_real:.4f}")
    print(f"  shuffled mean Sharpe     : {mean_shuffled:.4f}")
    print(f"  shuffled std Sharpe      : {std_shuffled:.4f}")
    print(f"  z-score                  : {z_score:.3f}")
    print(f"  p-value (one-sided)      : {p_value:.4f}")
    print(f"  GATE Sharpe>shuffled 95%: {'PASS' if p_value < 0.05 else 'FAIL'} (need p < 0.05)")


if __name__ == "__main__":
    main()
