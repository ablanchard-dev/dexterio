"""S+3 T2 — Sector momentum rotation 11 SPDR sectors.

Plan amendment S+3 frozen scope :
    - Univers : XLK, XLF, XLV, XLI, XLY, XLP, XLE, XLRE, XLU, XLB, XLC (11 SPDR sector ETFs)
    - Stratégie : ranking 6m return, top 3 equal-weight, monthly rebalance
    - Costs : 10 bps round-trip per turnover
    - Benchmarks : SPY buy-hold + equal-weight 11 sectors monthly
    - Métriques : Sharpe / CAGR / DD / Calmar / turnover + capture_summary applicable
    - Sub-sample 2019-2022 vs 2022-2025
    - Permutation 500 iter SI pas clean fail

Critère PASS : Sharpe ≥ 0.8 AND Calmar > best bench AND beat ≥1 bench AND robust cross-régime
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
from research.label_factory import capture_summary

DATA_DIR = backend_dir / "data" / "equities"
SECTORS_PATH = DATA_DIR / "sectors_11_prices_6.5y.parquet"
F2_DIR = backend_dir / "data" / "f2_daily"

SECTORS = ["XLK", "XLF", "XLV", "XLI", "XLY", "XLP", "XLE", "XLRE", "XLU", "XLB", "XLC"]
TC_BPS = 10.0
LOOKBACK_MONTHS = 6
TOP_N = 3
REBAL_DAYS = 21


def load_sector_prices() -> pd.DataFrame:
    df = pd.read_parquet(SECTORS_PATH)
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="close").sort_index().ffill().dropna()
    return pivot[SECTORS]  # ensure column order


def load_spy() -> pd.Series:
    df = pd.read_parquet(F2_DIR / "SPY_1d.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["Close"]


def _portfolio_metrics(eq: pd.Series, label: str) -> dict:
    if len(eq) < 30:
        return {"label": label, "valid": False}
    rets = eq.pct_change().dropna()
    final_ret = eq.iloc[-1] / eq.iloc[0] - 1
    days = (eq.index[-1] - eq.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd_series = eq / rm - 1
    max_dd = float(dd_series.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0
    monthly = eq.resample("ME").last().pct_change().dropna()
    pct_months_neg = float((monthly < 0).mean()) if len(monthly) > 0 else 0
    return {
        "label": label, "valid": True,
        "n_days": len(eq),
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": sharpe,
        "max_DD_pct": max_dd * 100,
        "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
        "pct_months_neg": pct_months_neg * 100,
    }


def run_sector_rotation(prices: pd.DataFrame, lookback_months: int = LOOKBACK_MONTHS,
                          top_n: int = TOP_N, rebal_days: int = REBAL_DAYS,
                          tc_bps: float = TC_BPS) -> tuple[pd.Series, list[dict], pd.DataFrame]:
    """Top-N momentum rotation across sectors.

    Returns (equity_curve, allocation_history, per_event_returns)
    """
    lookback_days = lookback_months * 21  # ~21 trading days/month
    n = len(prices)
    if n < lookback_days + rebal_days:
        raise ValueError("Not enough data")

    eq = pd.Series(1.0, index=prices.index)
    cur_eq = 1.0
    cur_weights: dict[str, float] = {}
    rebal_indices = list(range(lookback_days, n, rebal_days))
    tc_rate = tc_bps / 10000.0
    alloc_history = []
    per_position_perf = []

    for i in range(lookback_days, n):
        date = prices.index[i]
        if i in rebal_indices:
            # Compute 6m return per sector
            window_start = i - lookback_days
            returns_6m = prices.iloc[i] / prices.iloc[window_start] - 1
            top_sectors = returns_6m.nlargest(top_n).index.tolist()
            new_weights = {s: 1.0 / top_n for s in top_sectors}
            # Apply turnover cost
            all_sym = set(new_weights) | set(cur_weights)
            turnover = sum(abs(new_weights.get(s, 0) - cur_weights.get(s, 0)) for s in all_sym)
            cur_eq *= (1.0 - turnover * tc_rate)
            # Track per-position 21d-forward return for capture analysis
            for sec in top_sectors:
                if i + rebal_days < n:
                    fwd_ret = prices.iloc[i + rebal_days][sec] / prices.iloc[i][sec] - 1
                    # Compute peak / trough during hold
                    hold_window = prices.iloc[i:i + rebal_days + 1][sec]
                    peak = hold_window.max() / prices.iloc[i][sec] - 1
                    trough = hold_window.min() / prices.iloc[i][sec] - 1
                    per_position_perf.append({
                        "date": date,
                        "sector": sec,
                        "realized_ret": fwd_ret,
                        "peak_ret": peak,
                        "trough_ret": trough,
                    })
            cur_weights = new_weights
            alloc_history.append({"date": date, "top_sectors": top_sectors, "returns_6m": returns_6m.to_dict()})
        # Daily portfolio return
        if i > lookback_days and cur_weights:
            day_ret = sum(cur_weights.get(s, 0) * (prices.iloc[i][s] / prices.iloc[i-1][s] - 1)
                          for s in cur_weights)
            cur_eq *= (1.0 + day_ret)
        eq.iloc[i] = cur_eq

    eq = eq.iloc[lookback_days:].dropna()
    return eq, alloc_history, pd.DataFrame(per_position_perf)


def main() -> None:
    print("=" * 100)
    print(f"S+3 T2 — Sector momentum rotation 11 SPDR sectors (top {TOP_N} by {LOOKBACK_MONTHS}m return, monthly rebal)")
    print("=" * 100)
    prices = load_sector_prices()
    print(f"\nData : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {len(SECTORS)} sectors)")

    # Strategy
    print(f"\nRunning sector rotation (lookback={LOOKBACK_MONTHS}m, top {TOP_N}, monthly rebal, {TC_BPS} bps cost)...")
    eq_strat, alloc_hist, per_pos = run_sector_rotation(prices)
    metrics_strat = _portfolio_metrics(eq_strat, "Sector Momentum Top-3 6m")
    metrics_strat["n_rebalances"] = len(alloc_hist)

    # Benchmark : equal-weight 11 sectors monthly
    print("Running equal-weight 11 sectors benchmark...")
    alloc_ew = PortfolioAllocator(SECTORS)
    eq_ew, m_ew, _ = run_backtest(
        prices, alloc_ew, method="equal_weight",
        rebalance_freq_days=REBAL_DAYS,
        warmup_days=126,  # match strategy lookback start
        transaction_cost_bps=TC_BPS,
    )
    eq_ew = eq_ew.loc[eq_strat.index[0]:eq_strat.index[-1]]
    metrics_ew = _portfolio_metrics(eq_ew, "REF Equal-weight 11 sectors monthly")

    # Benchmark : SPY buy-hold same window
    spy = load_spy().loc[eq_strat.index[0]:eq_strat.index[-1]]
    eq_spy = spy / spy.iloc[0]
    metrics_spy = _portfolio_metrics(eq_spy, "REF SPY buy-and-hold")

    print()
    print("=" * 110)
    print(f"{'Strategy':<48} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} {'vol':>6} {'%mNeg':>7}")
    print("=" * 110)
    for m in [metrics_strat, metrics_spy, metrics_ew]:
        if not m.get("valid"):
            print(f"{m['label']:<48} INVALID")
            continue
        print(f"{m['label']:<48} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
              f"{m['vol_ann_pct']:>5.1f}% {m['pct_months_neg']:>6.1f}%")

    # Capture summary on per-position perf
    print()
    print("=" * 100)
    print("Niveau exploitation — capture_summary per-position 21d-forward returns")
    print("=" * 100)
    if not per_pos.empty:
        per_pos["peak_r"] = per_pos["peak_ret"] / 0.01  # R = 1%
        per_pos["r_multiple"] = per_pos["realized_ret"] / 0.01
        s = capture_summary(per_pos[["r_multiple", "peak_r"]].dropna())
        if s.get("n", 0) > 0:
            print(f"  n={s['n']:<5} cap_med={s['median_capture_ratio']:>+7.3f} "
                  f"%weak={s['pct_signal_weak']*100:>5.1f}% %early={s['pct_exit_early']*100:>5.1f}% "
                  f"%late={s['pct_exit_late']*100:>5.1f}% %eff={s['pct_efficient']*100:>5.1f}% "
                  f"→ {s['headline']}")

    # Sub-sample stability
    split_date = pd.Timestamp("2022-06-01")
    print()
    print("=" * 100)
    print("Sub-sample stability — 2019-2022 vs 2022-2025")
    print("=" * 100)

    def sub_sharpe(eq: pd.Series, start, end) -> tuple[float, float]:
        sub_eq = eq.loc[start:end]
        if len(sub_eq) < 30:
            return 0.0, 0.0
        rets = sub_eq.pct_change().dropna()
        if rets.std() == 0:
            return 0.0, 0.0
        sh = float(rets.mean() / rets.std() * np.sqrt(252))
        days = (sub_eq.index[-1] - sub_eq.index[0]).days
        years = days / 365.25
        cg = (sub_eq.iloc[-1] / sub_eq.iloc[0]) ** (1/years) - 1 if years > 0 else 0
        return sh, cg * 100

    for label, eq in [("Sector Momentum Top-3", eq_strat), ("SPY", eq_spy),
                        ("Equal-weight 11", eq_ew)]:
        sh1, cg1 = sub_sharpe(eq, eq.index[0], split_date)
        sh2, cg2 = sub_sharpe(eq, split_date, eq.index[-1])
        print(f"  {label:<35} 2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}%  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}%  | ΔSharpe={sh2-sh1:>+5.2f}")

    # Gate
    print()
    print("=" * 100)
    print("Gate plan S+3 T2")
    print("=" * 100)
    sh = metrics_strat["Sharpe_ann"]
    cal = metrics_strat["Calmar"]
    sh_spy = metrics_spy["Sharpe_ann"]
    sh_ew = metrics_ew["Sharpe_ann"]
    cal_spy = metrics_spy["Calmar"]
    cal_ew = metrics_ew["Calmar"]
    print(f"  Sector Mom Sharpe ≥ 0.8 : {'PASS' if sh >= 0.8 else 'FAIL'} (got {sh:.2f})")
    print(f"  Sector Mom Sharpe ≥ 0.5 (kill rule) : {'OK' if sh >= 0.5 else 'KILL'} (got {sh:.2f})")
    print(f"  Sector Mom Calmar > best bench ({max(cal_spy, cal_ew):.2f}) : "
          f"{'PASS' if cal > max(cal_spy, cal_ew) else 'FAIL'} (got {cal:.2f})")
    print(f"  Sector Mom Sharpe > best bench ({max(sh_spy, sh_ew):.2f}) : "
          f"{'PASS' if sh > max(sh_spy, sh_ew) else 'FAIL'} (got {sh:.2f})")

    # Save
    out_dir = backend_dir / "results" / "s3_t2_sector_momentum"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "sector_momentum": eq_strat,
        "SPY": eq_spy.reindex(eq_strat.index),
        "equal_weight_11": eq_ew.reindex(eq_strat.index),
    }).to_parquet(out_dir / "equity_curves.parquet")
    if not per_pos.empty:
        per_pos.to_parquet(out_dir / "per_position_perf.parquet", index=False)
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
