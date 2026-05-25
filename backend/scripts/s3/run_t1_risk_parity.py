"""S+3 T1 — Risk parity 9 ETFs vs benchmarks (SPY / 60-40 / equal-weight).

Plan amendment S+3 frozen scope :
    - Strategy : risk_parity (inverse-vol) sur 9 ETFs, monthly rebalance,
                 vol target 10% annualisé via overlay
    - Univers : SPY, QQQ, IWM, DIA, EFA, EEM, GLD, TLT, FXI (data déjà 6.5y)
    - Benchmarks (3) : SPY buy-hold, 60/40 SPY/TLT monthly rebal, equal-weight 9 ETFs
    - Costs : 10 bps round-trip per turnover
    - Métriques : Sharpe, CAGR, maxDD, Calmar (CAGR/|DD|), turnover ann,
                  % months negative, rolling 12m Sharpe min/median, DD duration max
    - Sub-sample 2019-2022 vs 2022-2025
    - Permutation 500 iter SI pas clean fail
    - Verdict G4 standard avec question explicite "vrai R ou défendable stat ?"

Critère PASS : Sharpe net ≥ 0.8 AND Calmar > au moins 1 benchmark AND beat ≥1 bench
                AND robust cross-régime (ΔSharpe < 0.4)

Usage : python backend/scripts/s3/run_t1_risk_parity.py
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
TC_BPS = 10.0


def load_prices() -> pd.DataFrame:
    frames = []
    for t in TICKERS:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def _portfolio_metrics(eq: pd.Series, label: str) -> dict:
    if len(eq) < 30:
        return {"label": label, "valid": False, "n_days": len(eq)}
    rets = eq.pct_change().dropna()
    final_ret = eq.iloc[-1] / eq.iloc[0] - 1
    days = (eq.index[-1] - eq.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd = (eq / rm - 1)
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0
    # Drawdown duration (longest underwater period)
    underwater = (dd < 0).astype(int)
    dd_periods = []
    cur = 0
    for v in underwater:
        if v:
            cur += 1
        else:
            if cur > 0:
                dd_periods.append(cur)
            cur = 0
    if cur > 0:
        dd_periods.append(cur)
    dd_dur_max = max(dd_periods) if dd_periods else 0
    # Months negative
    monthly = eq.resample("ME").last().pct_change().dropna()
    pct_months_neg = float((monthly < 0).mean()) if len(monthly) > 0 else 0
    # Rolling 12m Sharpe
    rolling_window = 252
    if len(rets) >= rolling_window:
        rolling_mean = rets.rolling(rolling_window).mean()
        rolling_std = rets.rolling(rolling_window).std()
        rolling_sharpe = (rolling_mean / rolling_std * np.sqrt(252)).dropna()
        rs_min = float(rolling_sharpe.min()) if len(rolling_sharpe) > 0 else 0
        rs_median = float(rolling_sharpe.median()) if len(rolling_sharpe) > 0 else 0
    else:
        rs_min = rs_median = 0
    return {
        "label": label,
        "n_days": len(eq),
        "total_return_pct": final_ret * 100,
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": sharpe,
        "max_DD_pct": max_dd * 100,
        "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
        "pct_months_neg": pct_months_neg * 100,
        "dd_duration_max_days": dd_dur_max,
        "rolling_12m_sharpe_min": rs_min,
        "rolling_12m_sharpe_median": rs_median,
        "valid": True,
    }


def benchmark_buy_hold(prices: pd.DataFrame, ticker: str) -> pd.Series:
    p = prices[ticker].dropna()
    return p / p.iloc[0]


def benchmark_60_40(prices: pd.DataFrame, rebal_freq_days: int = 21,
                     tc_bps: float = TC_BPS) -> pd.Series:
    """60% SPY + 40% TLT, monthly rebalance with cost."""
    spy = prices["SPY"].dropna()
    tlt = prices["TLT"].dropna()
    common = spy.index.intersection(tlt.index)
    spy = spy.loc[common]
    tlt = tlt.loc[common]
    n = len(common)
    rebal = list(range(0, n, rebal_freq_days))
    cur_spy_w, cur_tlt_w = 0.6, 0.4
    eq = pd.Series(1.0, index=common)
    cur_eq = 1.0
    tc_rate = tc_bps / 10000.0
    for i in range(1, n):
        if i in rebal:
            target_spy, target_tlt = 0.6, 0.4
            turnover = abs(target_spy - cur_spy_w) + abs(target_tlt - cur_tlt_w)
            cur_eq *= (1.0 - turnover * tc_rate)
            cur_spy_w, cur_tlt_w = target_spy, target_tlt
        spy_ret = spy.iloc[i] / spy.iloc[i-1] - 1
        tlt_ret = tlt.iloc[i] / tlt.iloc[i-1] - 1
        port_ret = cur_spy_w * spy_ret + cur_tlt_w * tlt_ret
        cur_eq *= (1.0 + port_ret)
        eq.iloc[i] = cur_eq
        # Drift weights
        cur_spy_w = cur_spy_w * (1 + spy_ret) / (1 + port_ret)
        cur_tlt_w = cur_tlt_w * (1 + tlt_ret) / (1 + port_ret)
    return eq


def main() -> None:
    print("=" * 100)
    print("S+3 T1 — Risk parity 9 ETFs vs benchmarks")
    print("=" * 100)
    prices = load_prices()
    print(f"\nData : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {len(TICKERS)} ETFs)")

    alloc = PortfolioAllocator(TICKERS)

    # ===== Strategy : Risk parity =====
    print("\nRunning risk_parity strategy (vol target 10% via overlay)...")
    eq_rp, m_rp, _ = run_backtest(
        prices, alloc, method="risk_parity",
        overlays=["vol_target"],
        rebalance_freq_days=21,
        warmup_days=120,  # 60d vol lookback + buffer
        transaction_cost_bps=TC_BPS,
        target_annual_vol=0.10,
    )
    metrics_rp = _portfolio_metrics(eq_rp, "Risk Parity 9 ETFs (vol target 10%)")
    metrics_rp["n_rebalances"] = m_rp.n_rebalances

    # ===== Benchmark 1 : SPY buy-and-hold =====
    eq_spy = benchmark_buy_hold(prices, "SPY")
    eq_spy = eq_spy.loc[eq_rp.index[0]:eq_rp.index[-1]]  # align window
    metrics_spy = _portfolio_metrics(eq_spy, "REF SPY buy-and-hold")

    # ===== Benchmark 2 : 60/40 SPY/TLT monthly =====
    eq_6040 = benchmark_60_40(prices, rebal_freq_days=21, tc_bps=TC_BPS)
    eq_6040 = eq_6040.loc[eq_rp.index[0]:eq_rp.index[-1]]
    metrics_6040 = _portfolio_metrics(eq_6040, "REF 60/40 SPY/TLT monthly rebal")

    # ===== Benchmark 3 : Equal-weight 9 ETFs monthly =====
    print("Running equal-weight 9 ETFs benchmark...")
    eq_ew, m_ew, _ = run_backtest(
        prices, alloc, method="equal_weight",
        rebalance_freq_days=21,
        warmup_days=120,
        transaction_cost_bps=TC_BPS,
    )
    metrics_ew = _portfolio_metrics(eq_ew, "REF Equal-weight 9 ETFs monthly")

    # ===== Print all metrics =====
    print()
    print("=" * 110)
    print(f"{'Strategy':<45} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} "
          f"{'vol':>6} {'%mNeg':>7} {'DDdur_d':>8}")
    print("=" * 110)
    for m in [metrics_rp, metrics_spy, metrics_6040, metrics_ew]:
        if not m.get("valid"):
            print(f"{m['label']:<45} INVALID")
            continue
        print(f"{m['label']:<45} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
              f"{m['vol_ann_pct']:>5.1f}% {m['pct_months_neg']:>6.1f}% "
              f"{m['dd_duration_max_days']:>8}")

    print()
    print("Rolling 12m Sharpe stability (lower = stable, more positive consistent):")
    for m in [metrics_rp, metrics_spy, metrics_6040, metrics_ew]:
        if not m.get("valid"):
            continue
        print(f"  {m['label']:<45} min={m['rolling_12m_sharpe_min']:>+5.2f}  "
              f"median={m['rolling_12m_sharpe_median']:>+5.2f}")

    # ===== Sub-sample stability =====
    split_date = pd.Timestamp("2022-06-01")
    print()
    print("=" * 100)
    print("Sub-sample stability — 2019-2022 vs 2022-2025")
    print("=" * 100)

    def sub_sharpe(eq: pd.Series, start, end) -> tuple[float, float, int]:
        sub_eq = eq.loc[start:end]
        if len(sub_eq) < 30:
            return 0.0, 0.0, len(sub_eq)
        rets = sub_eq.pct_change().dropna()
        if rets.std() == 0:
            return 0.0, 0.0, len(sub_eq)
        sh = float(rets.mean() / rets.std() * np.sqrt(252))
        days = (sub_eq.index[-1] - sub_eq.index[0]).days
        years = days / 365.25
        cg = (sub_eq.iloc[-1] / sub_eq.iloc[0]) ** (1/years) - 1 if years > 0 else 0
        return sh, cg * 100, len(sub_eq)

    for label, eq in [("Risk Parity 9 ETFs", eq_rp), ("SPY buy-hold", eq_spy),
                       ("60/40 SPY/TLT", eq_6040), ("Equal-weight 9 ETFs", eq_ew)]:
        sh1, cg1, n1 = sub_sharpe(eq, eq.index[0], split_date)
        sh2, cg2, n2 = sub_sharpe(eq, split_date, eq.index[-1])
        print(f"  {label:<35} 2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}%  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}%  | "
              f"ΔSharpe={sh2-sh1:>+5.2f}")

    # ===== Gate evaluation =====
    print()
    print("=" * 100)
    print("Gate plan S+3 T1 (criteria : Sharpe ≥ 0.8 AND Calmar > ≥1 bench AND beat ≥1 bench)")
    print("=" * 100)
    sh_rp = metrics_rp["Sharpe_ann"]
    cal_rp = metrics_rp["Calmar"]
    sh_spy = metrics_spy["Sharpe_ann"]
    sh_6040 = metrics_6040["Sharpe_ann"]
    sh_ew = metrics_ew["Sharpe_ann"]
    cal_spy = metrics_spy["Calmar"]
    cal_6040 = metrics_6040["Calmar"]
    cal_ew = metrics_ew["Calmar"]

    print(f"  Risk Parity Sharpe ≥ 0.8 : {'PASS' if sh_rp >= 0.8 else 'FAIL'} (got {sh_rp:.2f})")
    print(f"  Risk Parity Calmar > best benchmark Calmar : "
          f"{'PASS' if cal_rp > max(cal_spy, cal_6040, cal_ew) else 'FAIL'} "
          f"(got {cal_rp:.2f}, bench max = {max(cal_spy, cal_6040, cal_ew):.2f})")
    print(f"  Risk Parity Sharpe > best bench Sharpe : "
          f"{'PASS' if sh_rp > max(sh_spy, sh_6040, sh_ew) else 'FAIL'} "
          f"(got {sh_rp:.2f}, bench max = {max(sh_spy, sh_6040, sh_ew):.2f})")
    print(f"  Sub-sample stability (ΔSharpe < 0.4 absolu) : "
          f"see table above (qualitative)")
    print(f"  Kill rule Sharpe < 0.5 : "
          f"{'KILL' if sh_rp < 0.5 else 'OK'} (got {sh_rp:.2f})")

    # Save
    out_dir = backend_dir / "results" / "s3_t1_risk_parity"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "risk_parity": eq_rp,
        "SPY": eq_spy.reindex(eq_rp.index),
        "60_40": eq_6040.reindex(eq_rp.index),
        "equal_weight": eq_ew.reindex(eq_rp.index),
    }).to_parquet(out_dir / "equity_curves.parquet")
    print(f"\n[saved equity curves to {out_dir}]")


if __name__ == "__main__":
    main()
