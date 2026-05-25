"""Sprint Ultra-Final T_final_1b — TSMOM beta-neutralized validation.

Diagnostic post T_final_1 : TSMOM résiduel Sharpe +0.66 (alpha pur), seul des
5 strats. Mais sélection post-hoc parmi 5 → risque de selection bias.

Validation rigoureuse pré-promotion :
  1. Sharpe net hedge costs (beta change turnover)
  2. p-value simple permutation (1000 iter) : shuffle TSMOM returns only
  3. p-value max-stat family-wise (1000 iter) : shuffle 5 strats, max résiduel
     Sharpe parmi 5 vs TSMOM réel — corrige selection bias
  4. Sub-sample 2020-2022 vs 2022-2025
  5. Beta résiduel post-hedge (doit être proche de 0)
  6. Calmar défendable

Gate strict pour candidat Stage 2 :
  - Sharpe net hedge costs ≥ 0.5
  - p-value simple < 0.10
  - p-value max-stat < 0.10 (ou clearly close avec justification)
  - beta résiduel ≈ 0
  - sub-sample pas catastrophique
  - Calmar défendable

Frozen :
  - beta lookback 252d
  - hedge daily (no monthly choice post-hoc)
  - hedge cost 5 bps × |Δβ| daily
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_EQ = backend_dir / "data" / "equities"
DATA_F2 = backend_dir / "data" / "f2_daily"
RESULTS_DIR = backend_dir / "results"

BETA_LOOKBACK = 252
HEDGE_COST_BPS = 5.0
N_PERMUTATIONS = 1000
SEED = 42


def load_strategy_returns() -> pd.DataFrame:
    out = {}
    df = pd.read_parquet(DATA_EQ / "tsmom_4etf_daily_returns.parquet")
    out["tsmom"] = df["ret"]
    rp = pd.read_parquet(RESULTS_DIR / "s3_t1_risk_parity" / "equity_curves.parquet")
    out["risk_parity"] = rp["risk_parity"].pct_change().fillna(0)
    out["equal_weight_9"] = rp["equal_weight"].pct_change().fillna(0)
    sm = pd.read_parquet(RESULTS_DIR / "s3_t2_sector_momentum" / "equity_curves.parquet")
    out["sector_momentum"] = sm["sector_momentum"].pct_change().fillna(0)
    lv = pd.read_parquet(RESULTS_DIR / "s3_t3_low_vol" / "equity_curves.parquet")
    out["low_vol"] = lv["low_vol_decile"].pct_change().fillna(0)
    return pd.DataFrame(out).dropna()


def load_spy_returns(idx: pd.Index) -> pd.Series:
    spy_df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
    spy_df["date"] = pd.to_datetime(spy_df["date"])
    return spy_df.set_index("date")["Close"].pct_change().fillna(0).reindex(idx).fillna(0)


def rolling_beta_vec(strat: np.ndarray, spy: np.ndarray, lookback: int) -> np.ndarray:
    """Vectorized rolling beta. Returns NaN for first lookback bars.

    beta_t computed using strat[t-lookback+1:t+1] and spy[t-lookback+1:t+1] (inclusive).
    Then shifted by 1 to avoid lookahead → beta_t actually uses [t-lookback:t-1].
    """
    n = len(strat)
    out = np.full(n, np.nan)
    for i in range(lookback, n):
        s_window = strat[i - lookback:i]  # exclusive of t (no lookahead)
        m_window = spy[i - lookback:i]
        var_m = m_window.var()
        if var_m > 1e-12:
            out[i] = np.cov(s_window, m_window, ddof=1)[0, 1] / var_m
    return out


def hedged_returns_with_costs(strat_rets: np.ndarray, spy_rets: np.ndarray,
                                lookback: int = BETA_LOOKBACK,
                                hedge_cost_bps: float = HEDGE_COST_BPS
                                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute beta-neutralized strategy returns with hedge turnover costs.

    Returns (hedged_rets, beta_used, hedge_turnover_costs)
    """
    beta = rolling_beta_vec(strat_rets, spy_rets, lookback)
    # Apply hedge: hedged_t = strat_t - beta_(t-1) × spy_t (no lookahead)
    # We treat beta_t as already lagged (since rolling_beta_vec uses [t-lookback:t-1])
    # Hedge change cost: when beta changes between days, turnover in SPY hedge
    # cost_t = |beta_t - beta_(t-1)| × hedge_cost_bps / 10000
    hedged = np.full_like(strat_rets, np.nan)
    cost = np.full_like(strat_rets, 0.0)
    for i in range(len(strat_rets)):
        if np.isnan(beta[i]):
            continue
        # Apply hedge using beta of same row (already shifted via rolling_beta_vec)
        hedged[i] = strat_rets[i] - beta[i] * spy_rets[i]
        # Turnover cost
        if i > 0 and not np.isnan(beta[i - 1]):
            dbeta = abs(beta[i] - beta[i - 1])
            cost[i] = dbeta * (hedge_cost_bps / 10000.0)
            hedged[i] -= cost[i]
    return hedged, beta, cost


def sharpe_ann(rets: np.ndarray) -> float:
    valid = rets[~np.isnan(rets)]
    if len(valid) < 30 or valid.std() == 0:
        return 0.0
    return float(valid.mean() / valid.std() * np.sqrt(252))


def main() -> None:
    print("=" * 100)
    print("Sprint Ultra-Final T_final_1b — TSMOM beta-neutralized validation")
    print("=" * 100)

    rets_df = load_strategy_returns()
    spy = load_spy_returns(rets_df.index).values
    dates = rets_df.index

    # ===== Real TSMOM hedged with costs =====
    tsmom_real = rets_df["tsmom"].values
    hedged_real, beta_real, cost_real = hedged_returns_with_costs(
        tsmom_real, spy, BETA_LOOKBACK, HEDGE_COST_BPS
    )
    valid_mask = ~np.isnan(hedged_real)
    hedged_real_valid = hedged_real[valid_mask]
    real_sharpe = sharpe_ann(hedged_real)

    # Compute residual beta to verify hedge effectiveness
    residual_beta = np.cov(hedged_real_valid, spy[valid_mask])[0, 1] / spy[valid_mask].var()
    print(f"\nReal TSMOM hedged (252d beta, costs {HEDGE_COST_BPS} bps × |Δβ|) :")
    print(f"  Sharpe net : {real_sharpe:.4f}")
    print(f"  Mean daily cost : {cost_real[valid_mask].mean()*10000:.2f} bps")
    print(f"  Total hedge costs annualized : {cost_real[valid_mask].mean()*252*100:.2f}%")
    print(f"  Beta moyen : {beta_real[valid_mask].mean():.3f}")
    print(f"  Residual beta (post-hedge) : {residual_beta:+.4f} (target ~0)")
    print(f"  Hedged returns mean ann : {hedged_real_valid.mean()*252*100:+.2f}%")
    print(f"  Hedged vol ann : {hedged_real_valid.std()*np.sqrt(252)*100:.2f}%")

    # Equity curve
    eq = (1 + np.nan_to_num(hedged_real, 0.0)).cumprod()
    rm = np.maximum.accumulate(eq)
    dd = (eq / rm - 1).min()
    days = (dates[-1] - dates[0]).days
    years = days / 365.25
    cagr = eq[-1] ** (1/years) - 1
    calmar = cagr / abs(dd) if dd < 0 else 0
    print(f"  CAGR : {cagr*100:+.2f}%  maxDD : {dd*100:+.1f}%  Calmar : {calmar:+.2f}")

    # ===== Sub-sample =====
    print("\nSub-sample analysis :")
    split_date = pd.Timestamp("2022-06-01")
    split_idx = (dates < split_date).sum()
    sub1 = hedged_real[:split_idx][~np.isnan(hedged_real[:split_idx])]
    sub2 = hedged_real[split_idx:][~np.isnan(hedged_real[split_idx:])]
    sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if len(sub1) > 30 and sub1.std() > 0 else 0
    sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if len(sub2) > 30 and sub2.std() > 0 else 0
    cg1 = ((1 + sub1).prod()) ** (252/len(sub1)) - 1 if len(sub1) > 30 else 0
    cg2 = ((1 + sub2).prod()) ** (252/len(sub2)) - 1 if len(sub2) > 30 else 0
    print(f"  2020-2022 (n={len(sub1)}) : Sharpe={sh1:+.3f}  CAGR={cg1*100:+.2f}%")
    print(f"  2022-2025 (n={len(sub2)}) : Sharpe={sh2:+.3f}  CAGR={cg2*100:+.2f}%")
    print(f"  ΔSharpe = {sh2 - sh1:+.3f}")

    # ===== Permutation simple (TSMOM only) =====
    print(f"\n=== Permutation SIMPLE 1000 iter (shuffle TSMOM only, SPY fixe) ===")
    rng = np.random.default_rng(SEED)
    sharpes_simple = []
    t0 = time.time()
    for i in range(N_PERMUTATIONS):
        shuffled = rng.permutation(tsmom_real)
        h, _, _ = hedged_returns_with_costs(shuffled, spy, BETA_LOOKBACK, HEDGE_COST_BPS)
        sharpes_simple.append(sharpe_ann(h))
        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            rate = (i+1) / elapsed
            eta = (N_PERMUTATIONS - i - 1) / rate
            mean_so_far = np.mean(sharpes_simple)
            p_so_far = np.mean([s >= real_sharpe for s in sharpes_simple])
            print(f"  iter {i+1}/{N_PERMUTATIONS} | rate {rate:.1f}/s | ETA {eta:.0f}s | "
                  f"mean_perm={mean_so_far:.3f} | p_simple_so_far={p_so_far:.4f}")

    sharpes_simple = np.array(sharpes_simple)
    p_simple = float((sharpes_simple >= real_sharpe).mean())
    mean_simple = sharpes_simple.mean()
    std_simple = sharpes_simple.std()
    print(f"  Simple permutation result : real={real_sharpe:.4f} vs perm_mean={mean_simple:.4f} "
          f"std={std_simple:.4f}")
    print(f"  p-value simple : {p_simple:.4f}")

    # ===== Permutation MAX-STAT (5 strats, max résiduel Sharpe) =====
    print(f"\n=== Permutation MAX-STAT 1000 iter (shuffle 5 strats, max résiduel) ===")
    print("  Corrige selection bias : nous avons choisi TSMOM parmi 5 strats")
    rng_ms = np.random.default_rng(SEED)
    max_sharpes = []
    t0 = time.time()
    strat_arrays = {col: rets_df[col].values for col in rets_df.columns}
    for i in range(N_PERMUTATIONS):
        per_strat_sharpes = []
        for col in rets_df.columns:
            shuffled = rng_ms.permutation(strat_arrays[col])
            h, _, _ = hedged_returns_with_costs(shuffled, spy, BETA_LOOKBACK, HEDGE_COST_BPS)
            per_strat_sharpes.append(sharpe_ann(h))
        max_sharpes.append(max(per_strat_sharpes))
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i+1) / elapsed
            eta = (N_PERMUTATIONS - i - 1) / rate
            mean_max = np.mean(max_sharpes)
            p_so_far = np.mean([s >= real_sharpe for s in max_sharpes])
            print(f"  iter {i+1}/{N_PERMUTATIONS} | rate {rate:.1f}/s | ETA {eta:.0f}s | "
                  f"mean_max_perm={mean_max:.3f} | p_maxstat_so_far={p_so_far:.4f}")

    max_sharpes = np.array(max_sharpes)
    p_maxstat = float((max_sharpes >= real_sharpe).mean())
    mean_max = max_sharpes.mean()
    std_max = max_sharpes.std()
    p95_max = np.percentile(max_sharpes, 95)
    print(f"  Max-stat result : real={real_sharpe:.4f} vs perm_max_mean={mean_max:.4f} "
          f"std={std_max:.4f}")
    print(f"  perm_max_p95={p95_max:.3f}")
    print(f"  p-value max-stat : {p_maxstat:.4f}")

    # ===== Verdict =====
    print()
    print("=" * 100)
    print("Verdict T_final_1b TSMOM hedgé validation")
    print("=" * 100)
    print(f"  1. Sharpe net hedge costs ≥ 0.5    : "
          f"{'PASS' if real_sharpe >= 0.5 else 'FAIL'} (got {real_sharpe:.3f})")
    print(f"  2. p-value simple < 0.10          : "
          f"{'PASS' if p_simple < 0.10 else 'FAIL'} (got {p_simple:.4f})")
    print(f"  3. p-value max-stat < 0.10        : "
          f"{'PASS' if p_maxstat < 0.10 else 'FAIL'} (got {p_maxstat:.4f})")
    print(f"  4. Beta résiduel ≈ 0 (|β| < 0.1)  : "
          f"{'PASS' if abs(residual_beta) < 0.1 else 'FAIL'} (got {residual_beta:+.4f})")
    print(f"  5. Sub-sample pas catastrophique  : "
          f"{'PASS' if abs(sh1 - sh2) < 1.0 and min(sh1, sh2) > -0.3 else 'FAIL'} "
          f"(2019-22:{sh1:+.2f} / 2022-25:{sh2:+.2f})")
    print(f"  6. Calmar défendable (>0.3)       : "
          f"{'PASS' if calmar > 0.3 else 'FAIL'} (got {calmar:+.3f})")

    # Decision
    gates_passed = sum([
        real_sharpe >= 0.5,
        p_simple < 0.10,
        p_maxstat < 0.10,
        abs(residual_beta) < 0.1,
        abs(sh1 - sh2) < 1.0 and min(sh1, sh2) > -0.3,
        calmar > 0.3,
    ])
    print()
    if gates_passed >= 5:
        print(f"  ✅ {gates_passed}/6 gates PASS → CANDIDAT STAGE 2 TSMOM hedgé")
    elif gates_passed >= 3:
        print(f"  ⚠️  {gates_passed}/6 gates PASS → MARGINAL / WATCHLIST non-promoted")
    else:
        print(f"  ❌ {gates_passed}/6 gates PASS → ARCHIVE marginal alpha non-significatif")

    # Save
    out_dir = backend_dir / "results" / "ultra_final_t1b_tsmom_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "tsmom_hedged_eq": eq,
        "tsmom_unhedged_eq": (1 + tsmom_real).cumprod(),
        "spy_eq": (1 + spy).cumprod(),
    }, index=dates).to_parquet(out_dir / "equity_curves.parquet")
    pd.DataFrame({
        "permutation_simple_sharpe": sharpes_simple,
        "permutation_maxstat_sharpe": max_sharpes,
    }).to_parquet(out_dir / "permutation_distributions.parquet")
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
