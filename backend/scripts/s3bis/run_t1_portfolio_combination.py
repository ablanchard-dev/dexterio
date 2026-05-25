"""S+3-bis T1 — Portfolio combination rolling no-lookahead.

Idée corpus : 9HD6xo2iO1g (Sharpe √N portfolio uncorrelated) + 9Y3yaoi9rUQ
(PyPortfolioOpt EfficientFrontier max_sharpe).

Asset naturel : multi-asset portfolio par construction.

Inputs (5 stratégies daily returns) :
  - TSMOM 4 ETFs SPY/QQQ/GLD/TLT (re-run persisted 2026-04-26)
  - Risk Parity 9 ETFs vol_target 10% (S+3 T1)
  - Sector Momentum Top-3 6m (S+3 T2)
  - Low-Vol Bottom Decile SP500 (S+3 T3)
  - Equal-Weight 9 ETFs monthly (S+3 T1 control)

Méthode :
  - Common date intersection
  - Rolling 12-month covariance + mean returns (lookback 252 days)
  - Re-optimize monthly (last day of month)
  - Bornes : weights ∈ [0.05, 0.40] each strategy
  - 5 bps turnover cost per re-balance
  - **No lookahead** : weights at month-end use ONLY data strictly < t

5 contrôles obligatoires :
  - V1 : combo optimized (max_sharpe via PyPortfolioOpt)
  - V2 : combo equal-weight (1/5 each, monthly rebal)
  - V3 : combo inverse-vol (1/std_strat, monthly rebal)
  - REF1 : SPY buy-hold
  - REF2 : 60/40 SPY/TLT

Verdict dur :
  - PASS : Sharpe net > 0.8 AND Calmar > SPY 0.43 AND beat ≥1 benchmark
            sur Sharpe ET Calmar simultanément AND sub-sample stable
  - KILL : Sharpe < 0.5
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from pypfopt import EfficientFrontier
from pypfopt import expected_returns, risk_models

# Cost model
TURNOVER_COST_BPS = 5.0
LOOKBACK_DAYS = 252
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.40

DATA_EQ = backend_dir / "data" / "equities"
DATA_F2 = backend_dir / "data" / "f2_daily"
RESULTS_DIR = backend_dir / "results"


def load_strategy_returns() -> pd.DataFrame:
    """Load 5 strategy daily returns into wide DataFrame."""
    out = {}

    # 1. TSMOM (just persisted)
    df = pd.read_parquet(DATA_EQ / "tsmom_4etf_daily_returns.parquet")
    out["tsmom"] = df["ret"]

    # 2. Risk Parity from S+3 T1 equity_curves.parquet
    rp_path = RESULTS_DIR / "s3_t1_risk_parity" / "equity_curves.parquet"
    rp_df = pd.read_parquet(rp_path)
    out["risk_parity"] = rp_df["risk_parity"].pct_change().fillna(0)
    out["equal_weight_9"] = rp_df["equal_weight"].pct_change().fillna(0)

    # 3. Sector Momentum from S+3 T2
    sm_path = RESULTS_DIR / "s3_t2_sector_momentum" / "equity_curves.parquet"
    sm_df = pd.read_parquet(sm_path)
    out["sector_momentum"] = sm_df["sector_momentum"].pct_change().fillna(0)

    # 4. Low-Vol from S+3 T3
    lv_path = RESULTS_DIR / "s3_t3_low_vol" / "equity_curves.parquet"
    lv_df = pd.read_parquet(lv_path)
    out["low_vol"] = lv_df["low_vol_decile"].pct_change().fillna(0)

    df = pd.DataFrame(out)
    # Common index (intersection)
    df = df.dropna()
    print(f"Strategy returns aligned : {len(df)} days, "
          f"{df.index[0].date()} → {df.index[-1].date()}")
    print(f"Per-strategy mean Sharpe (annualized) :")
    for col in df.columns:
        ret = df[col]
        sh = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
        print(f"  {col:<20} Sharpe={sh:+.3f}  vol={ret.std()*np.sqrt(252)*100:.1f}%")
    return df


def rolling_optimized_weights(returns_df: pd.DataFrame,
                                lookback_days: int = LOOKBACK_DAYS,
                                min_w: float = MIN_WEIGHT,
                                max_w: float = MAX_WEIGHT
                                ) -> pd.DataFrame:
    """Rolling out-of-sample max_sharpe weights (monthly re-optimize)."""
    n = len(returns_df)
    weights_history = pd.DataFrame(0.0, index=returns_df.index,
                                     columns=returns_df.columns)
    cur_weights = None
    rebal_dates = []
    # Build monthly re-balance dates : last trading day of each month
    monthly_last = returns_df.resample("ME").last().index
    monthly_last_set = set(monthly_last)

    for i, date in enumerate(returns_df.index):
        # Determine if today is a re-balance date OR first valid date
        is_rebalance_date = (date in monthly_last_set) and (i >= lookback_days)
        first_valid = (i == lookback_days)

        if is_rebalance_date or first_valid:
            window = returns_df.iloc[i - lookback_days:i]
            if window.std().min() <= 0:
                # degenerate: skip this rebalance
                pass
            else:
                try:
                    mu = expected_returns.mean_historical_return(
                        (1 + window).cumprod(), frequency=252, compounding=False
                    )
                    S = risk_models.sample_cov(
                        (1 + window).cumprod(), frequency=252
                    )
                    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
                    cur_weights = ef.max_sharpe(risk_free_rate=0.0)
                    cur_weights = pd.Series(cur_weights)
                    rebal_dates.append(date)
                except Exception as e:
                    # If optimization fails, keep prior weights
                    pass

        if cur_weights is not None:
            weights_history.loc[date] = cur_weights

    print(f"  optimized : {len(rebal_dates)} re-optimizations")
    return weights_history


def equal_weight_weights(returns_df: pd.DataFrame,
                          lookback_days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """1/N equal weight, applied from lookback_days onward."""
    n_strats = returns_df.shape[1]
    w = pd.DataFrame(1.0 / n_strats, index=returns_df.index,
                      columns=returns_df.columns)
    w.iloc[:lookback_days] = 0.0
    return w


def inverse_vol_weights(returns_df: pd.DataFrame,
                         lookback_days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """Inverse-vol weights monthly re-balance."""
    weights_history = pd.DataFrame(0.0, index=returns_df.index,
                                     columns=returns_df.columns)
    cur_weights = None
    monthly_last = returns_df.resample("ME").last().index
    monthly_last_set = set(monthly_last)

    for i, date in enumerate(returns_df.index):
        is_rebalance = (date in monthly_last_set) and (i >= lookback_days)
        first_valid = (i == lookback_days)
        if is_rebalance or first_valid:
            window = returns_df.iloc[i - lookback_days:i]
            vols = window.std()
            inv_vol = 1.0 / vols.replace(0, np.nan)
            inv_vol = inv_vol.dropna()
            if inv_vol.empty:
                continue
            w = inv_vol / inv_vol.sum()
            cur_weights = w
        if cur_weights is not None:
            weights_history.loc[date] = cur_weights
    return weights_history


def apply_weights(returns_df: pd.DataFrame, weights_df: pd.DataFrame,
                   turnover_cost_bps: float = TURNOVER_COST_BPS) -> pd.Series:
    """Apply weights to returns + turnover cost. Both strict no-lookahead :
    weights[t] are estimated using data < t, applied to returns[t]."""
    aligned_w = weights_df.shift(1).fillna(0)  # use yesterday's weights for today's return
    daily_ret = (aligned_w * returns_df).sum(axis=1)
    # Turnover cost
    turnover = (weights_df.diff().abs().sum(axis=1)).fillna(0)
    cost = turnover * (turnover_cost_bps / 10000.0)
    daily_ret_net = daily_ret - cost
    return daily_ret_net


def compute_metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    if len(rets) < 30:
        return {"label": label, "valid": False}
    eq = (1 + rets).cumprod()
    final_ret = eq.iloc[-1] - 1
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd_series = eq / rm - 1
    max_dd = float(dd_series.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0
    monthly = eq.resample("ME").last().pct_change().dropna()
    pct_months_neg = float((monthly < 0).mean()) if len(monthly) > 0 else 0
    return {
        "label": label, "valid": True,
        "n_days": len(rets),
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": float(sharpe),
        "max_DD_pct": max_dd * 100,
        "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
        "pct_months_neg": pct_months_neg * 100,
    }


def load_spy_60_40() -> tuple[pd.Series, pd.Series]:
    """Load SPY buy-hold + 60/40 SPY/TLT for benchmarks."""
    spy_df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
    spy_df["date"] = pd.to_datetime(spy_df["date"])
    spy = spy_df.set_index("date")["Close"]

    tlt_df = pd.read_parquet(DATA_F2 / "TLT_1d.parquet")
    tlt_df["date"] = pd.to_datetime(tlt_df["date"])
    tlt = tlt_df.set_index("date")["Close"]

    common = spy.index.intersection(tlt.index)
    spy, tlt = spy.loc[common], tlt.loc[common]
    spy_ret = spy.pct_change().fillna(0)

    # 60/40 monthly rebalance with 5bps turnover
    monthly_last = spy.resample("ME").last().index
    monthly_set = set(monthly_last)
    cur_w_spy, cur_w_tlt = 0.6, 0.4
    eq_6040 = pd.Series(1.0, index=spy.index)
    cur_eq = 1.0
    for i in range(1, len(spy)):
        date = spy.index[i]
        if date in monthly_set:
            target_spy, target_tlt = 0.6, 0.4
            turnover = abs(target_spy - cur_w_spy) + abs(target_tlt - cur_w_tlt)
            cur_eq *= (1 - turnover * 0.0005)
            cur_w_spy, cur_w_tlt = target_spy, target_tlt
        spy_r = spy.iloc[i] / spy.iloc[i - 1] - 1
        tlt_r = tlt.iloc[i] / tlt.iloc[i - 1] - 1
        port_r = cur_w_spy * spy_r + cur_w_tlt * tlt_r
        cur_eq *= (1 + port_r)
        eq_6040.iloc[i] = cur_eq
        # weight drift
        cur_w_spy = cur_w_spy * (1 + spy_r) / (1 + port_r)
        cur_w_tlt = cur_w_tlt * (1 + tlt_r) / (1 + port_r)
    return spy_ret, eq_6040.pct_change().fillna(0)


def main() -> None:
    print("=" * 100)
    print("S+3-bis T1 — Portfolio combination rolling no-lookahead")
    print("=" * 100)

    rets_df = load_strategy_returns()

    print()
    print("=== Computing weights (rolling 12m, monthly re-balance) ===")
    print("V1 optimized max_sharpe (PyPortfolioOpt) :")
    w_opt = rolling_optimized_weights(rets_df)
    print("V2 equal-weight :")
    w_ew = equal_weight_weights(rets_df)
    print("V3 inverse-vol :")
    w_iv = inverse_vol_weights(rets_df)

    # Apply
    rets_v1 = apply_weights(rets_df, w_opt)
    rets_v2 = apply_weights(rets_df, w_ew)
    rets_v3 = apply_weights(rets_df, w_iv)

    # Restrict to dates where we have all valid (skip warmup)
    valid_start = rets_df.index[LOOKBACK_DAYS]
    rets_v1 = rets_v1.loc[valid_start:]
    rets_v2 = rets_v2.loc[valid_start:]
    rets_v3 = rets_v3.loc[valid_start:]

    # Benchmarks
    spy_ret, ret_6040 = load_spy_60_40()
    spy_ret = spy_ret.loc[valid_start:rets_v1.index[-1]]
    ret_6040 = ret_6040.loc[valid_start:rets_v1.index[-1]]

    # Metrics
    metrics = []
    metrics.append(compute_metrics(rets_v1, "V1 combo optimized max_sharpe"))
    metrics.append(compute_metrics(rets_v2, "V2 combo equal-weight 1/5"))
    metrics.append(compute_metrics(rets_v3, "V3 combo inverse-vol"))
    metrics.append(compute_metrics(spy_ret, "REF1 SPY buy-hold"))
    metrics.append(compute_metrics(ret_6040, "REF2 60/40 SPY/TLT monthly"))

    print()
    print("=" * 110)
    print(f"{'Strategy':<48} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} {'vol':>6} {'%mNeg':>7}")
    print("=" * 110)
    for m in metrics:
        if not m.get("valid"):
            print(f"{m['label']:<48} INVALID")
            continue
        print(f"{m['label']:<48} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
              f"{m['vol_ann_pct']:>5.1f}% {m['pct_months_neg']:>6.1f}%")

    # Sub-sample
    split_date = pd.Timestamp("2022-06-01")
    print()
    print("=" * 100)
    print("Sub-sample stability — 2019-2022 vs 2022-2025")
    print("=" * 100)

    def sub(rets, start, end):
        r = rets.loc[start:end].dropna()
        if len(r) < 30 or r.std() == 0:
            return 0.0, 0.0
        sh = r.mean() / r.std() * np.sqrt(252)
        eq = (1 + r).cumprod()
        ye = (r.index[-1] - r.index[0]).days / 365.25
        cg = eq.iloc[-1] ** (1 / ye) - 1 if ye > 0 else 0
        return float(sh), cg * 100

    for label, rets in [("V1 optimized", rets_v1), ("V2 equal-weight", rets_v2),
                          ("V3 inverse-vol", rets_v3), ("SPY", spy_ret),
                          ("60/40", ret_6040)]:
        sh1, cg1 = sub(rets, rets.index[0], split_date)
        sh2, cg2 = sub(rets, split_date, rets.index[-1])
        print(f"  {label:<25} 2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}%  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}%  | ΔSharpe={sh2-sh1:>+5.2f}")

    # Gate
    print()
    print("=" * 100)
    print("Gate plan S+3-bis T1")
    print("=" * 100)
    for m in metrics[:3]:
        if not m.get("valid"):
            continue
        sh = m["Sharpe_ann"]
        cal = m["Calmar"]
        sh_spy = metrics[3]["Sharpe_ann"]
        sh_6040 = metrics[4]["Sharpe_ann"]
        cal_spy = metrics[3]["Calmar"]
        cal_6040 = metrics[4]["Calmar"]
        sh_v2 = metrics[1]["Sharpe_ann"]
        cal_v2 = metrics[1]["Calmar"]
        print(f"\n  {m['label']} :")
        print(f"    Sharpe ≥ 0.8 (PASS bar) : {'PASS' if sh >= 0.8 else 'FAIL'} (got {sh:.2f})")
        print(f"    Sharpe ≥ 0.5 (kill rule) : {'OK' if sh >= 0.5 else 'KILL'} (got {sh:.2f})")
        print(f"    Calmar > SPY ({cal_spy:.2f}) : {'PASS' if cal > cal_spy else 'FAIL'} (got {cal:.2f})")
        print(f"    Sharpe > best benchmark ({max(sh_spy, sh_6040, sh_v2):.2f}) : "
              f"{'PASS' if sh > max(sh_spy, sh_6040, sh_v2) else 'FAIL'}")

    # Save
    out_dir = RESULTS_DIR / "s3bis_t1_portfolio_combo"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "v1_optimized": (1 + rets_v1).cumprod(),
        "v2_equal_weight": (1 + rets_v2).cumprod(),
        "v3_inverse_vol": (1 + rets_v3).cumprod(),
        "spy": (1 + spy_ret).cumprod(),
        "60_40": (1 + ret_6040).cumprod(),
    }).to_parquet(out_dir / "equity_curves.parquet")
    w_opt.to_parquet(out_dir / "weights_optimized.parquet")
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
