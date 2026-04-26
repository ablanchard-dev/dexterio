"""F2 panic regime permutation — validate Sharpe 1.69 (n=92) on VIX>=30 days.

Per run_f2_fertile_longterm.py : fertile regime (VIX 15-25) was bull artifact
(6.5y Sharpe 0.57 vs 2y 2.30). BUT panic regime (VIX>=30) showed 6.5y Sharpe
**1.69** on n=92 days (contrib +16%) — only robust long-term positive.

Question : is this a real conditional edge or sample luck on 92 days ?

Méthode (simple conditional bootstrap) :
  1. Real daily returns partitionés par régime VIX prior-day.
  2. Real panic sample : n=92 jours, Sharpe ≈ 1.69.
  3. Null hypothesis : random subset de 92 jours dans full 6.5y returns
     a une Sharpe distribuée autour de Sharpe_full ≈ 0.73.
  4. Pour chaque iter : échantillonner 92 jours au hasard (sans remise), Sharpe.
  5. p-value = fraction des random samples Sharpe >= real panic Sharpe.
  6. PASS si p < 0.05.

Caveat : ce n'est pas un bar-shuffle strict (on ne peut pas recompute la
stratégie sur un subset de jours sans brouiller le rebalancing), c'est un
**bootstrap conditionnel** sur les returns post-fait. Il teste : est-ce que
92 jours tirés au hasard font aussi bien que les 92 panic days ?

Usage : python backend/scripts/f2/run_f2_panic_permutation.py
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
N_BOOT = 5000
SEED = 42


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


def sharpe_ann(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def main() -> None:
    prices = load_prices()
    vix = load_vix()
    alloc = PortfolioAllocator(TICKERS)
    equity, metrics, _ = run_backtest(
        prices, alloc, method="momentum",
        rebalance_freq_days=21, warmup_days=252,
        transaction_cost_bps=10.0,
        jt_lookback=12, jt_skip=1, jt_top_n=3,
    )
    returns = equity.pct_change().dropna()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()}")
    print(f"Full momentum J&T 6.5y Sharpe={metrics.sharpe_daily_annualized:.3f}")

    # Panic regime subset
    aligned_idx = returns.index.intersection(vix.index)
    vx_prior = vix.loc[aligned_idx].shift(1)
    panic_mask = vx_prior >= 30
    r_panic = returns.loc[aligned_idx][panic_mask].dropna()
    n_panic = len(r_panic)
    sharpe_panic = sharpe_ann(r_panic)
    print(f"Panic (VIX>=30) : n={n_panic}, Sharpe={sharpe_panic:.3f}, "
          f"mean_bps={r_panic.mean()*10000:.1f}, total_contrib={r_panic.sum()*100:.2f}%")
    print()

    # Conditional bootstrap : draw n_panic days at random from full 6.5y, Sharpe.
    rng = np.random.default_rng(SEED)
    full_returns = returns.loc[aligned_idx].dropna().values
    boot_sharpes = []
    for _ in range(N_BOOT):
        sample_idx = rng.choice(len(full_returns), size=n_panic, replace=False)
        sample = full_returns[sample_idx]
        if sample.std() == 0:
            boot_sharpes.append(0.0)
            continue
        boot_sharpes.append(float(sample.mean() / sample.std() * np.sqrt(252)))

    boot_sharpes = np.array(boot_sharpes)
    mean_boot = float(boot_sharpes.mean())
    std_boot = float(boot_sharpes.std())
    p_value = float((boot_sharpes >= sharpe_panic).mean())
    z_score = (sharpe_panic - mean_boot) / std_boot if std_boot > 0 else 0
    p99 = float(np.percentile(boot_sharpes, 99))
    p95 = float(np.percentile(boot_sharpes, 95))
    p90 = float(np.percentile(boot_sharpes, 90))

    print(f"=== Conditional bootstrap ({N_BOOT} iter, seed={SEED}) ===")
    print(f"  real panic Sharpe            : {sharpe_panic:.3f}")
    print(f"  bootstrap mean Sharpe        : {mean_boot:.3f}")
    print(f"  bootstrap std Sharpe         : {std_boot:.3f}")
    print(f"  bootstrap p90 / p95 / p99    : {p90:.3f} / {p95:.3f} / {p99:.3f}")
    print(f"  z-score                      : {z_score:.3f}")
    print(f"  p-value (one-sided)          : {p_value:.4f}")
    print(f"  GATE p<0.05                  : {'PASS' if p_value < 0.05 else 'FAIL'}")


if __name__ == "__main__":
    main()
