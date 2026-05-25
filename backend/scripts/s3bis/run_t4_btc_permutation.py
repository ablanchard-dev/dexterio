"""S+3-bis T4 BTC Donchian permutation test 500 iter.

Borderline PASS Sharpe 0.761 vs BTC buy-hold 0.744 (+0.017 narrow).
Permutation test obligatoire par discipline plan : shuffle daily returns BTC,
re-run Donchian, comparer Sharpe permuted vs réel.

Si p<0.10 = vrai signal validé.
Si p>0.10 = noise = MARGINAL ARCHIVE.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_CRYPTO = backend_dir / "data" / "crypto"

DONCHIAN_HIGH = 20
DONCHIAN_LOW = 10
COST_BPS = 5.0
N_PERMUTATIONS = 500
SEED = 42


def donchian_strategy_returns(prices: pd.Series) -> pd.Series:
    rolling_high = prices.rolling(DONCHIAN_HIGH).max()
    rolling_low = prices.rolling(DONCHIAN_LOW).min()
    rets = prices.pct_change().fillna(0)
    position = pd.Series(0.0, index=prices.index)
    cur_pos = 0
    for i in range(len(prices)):
        if pd.isna(rolling_high.iloc[i]) or pd.isna(rolling_low.iloc[i]):
            continue
        price = prices.iloc[i]
        if cur_pos == 0:
            if price > rolling_high.iloc[max(0, i-1)]:
                cur_pos = 1
        else:
            if price < rolling_low.iloc[max(0, i-1)]:
                cur_pos = 0
        position.iloc[i] = cur_pos
    daily_strat = position.shift(1).fillna(0) * rets
    pos_change = position.diff().abs().fillna(0)
    cost = pos_change * (COST_BPS / 10000.0)
    return daily_strat - cost


def sharpe_ann(rets: pd.Series) -> float:
    rets = rets.dropna()
    if len(rets) < 30 or rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * np.sqrt(252))


def permute_prices(prices: pd.Series, rng: np.random.Generator) -> pd.Series:
    """Shuffle daily returns, reconstruct prices."""
    rets = prices.pct_change().dropna().values
    shuffled = rng.permutation(rets)
    cumulative = np.concatenate([[prices.iloc[0]],
                                  prices.iloc[0] * np.cumprod(1 + shuffled)])
    return pd.Series(cumulative[:len(prices)], index=prices.index)


def main() -> None:
    df = pd.read_parquet(DATA_CRYPTO / "BTCUSDT_spot_1d_6.5y.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.tz_localize(None).dt.normalize()
    prices = df.set_index("date")["close"].sort_index()

    real_strat_rets = donchian_strategy_returns(prices)
    real_sharpe = sharpe_ann(real_strat_rets)
    print(f"Real BTC Donchian Sharpe : {real_sharpe:.4f}")
    print(f"Running {N_PERMUTATIONS} permutations seed={SEED}...")

    rng = np.random.default_rng(SEED)
    permuted_sharpes = []
    import time
    t0 = time.time()
    for i in range(N_PERMUTATIONS):
        perm_prices = permute_prices(prices, rng)
        perm_strat_rets = donchian_strategy_returns(perm_prices)
        permuted_sharpes.append(sharpe_ann(perm_strat_rets))
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (N_PERMUTATIONS - i - 1) / rate
            mean_so_far = np.mean(permuted_sharpes)
            p_so_far = np.mean([s >= real_sharpe for s in permuted_sharpes])
            print(f"  iter {i+1}/{N_PERMUTATIONS} | rate {rate:.1f}/s | ETA {eta:.0f}s | "
                  f"mean_perm_sharpe={mean_so_far:.3f} | p_so_far={p_so_far:.4f}")

    permuted_sharpes = np.array(permuted_sharpes)
    mean_perm = float(permuted_sharpes.mean())
    std_perm = float(permuted_sharpes.std())
    p_value = float((permuted_sharpes >= real_sharpe).mean())
    z_score = (real_sharpe - mean_perm) / std_perm if std_perm > 0 else 0
    p95 = float(np.percentile(permuted_sharpes, 95))
    p99 = float(np.percentile(permuted_sharpes, 99))

    print()
    print("=" * 80)
    print(f"Real BTC Donchian Sharpe   : {real_sharpe:.4f}")
    print(f"Permuted mean Sharpe       : {mean_perm:.4f}")
    print(f"Permuted std Sharpe        : {std_perm:.4f}")
    print(f"Permuted p95/p99           : {p95:.3f} / {p99:.3f}")
    print(f"z-score                    : {z_score:.3f}")
    print(f"p-value (one-sided)        : {p_value:.4f}")
    print(f"GATE p<0.10 (PASS)         : {'PASS' if p_value < 0.10 else 'FAIL'}")
    print(f"GATE p<0.05 (strong PASS)  : {'STRONG PASS' if p_value < 0.05 else 'NO'}")


if __name__ == "__main__":
    main()
