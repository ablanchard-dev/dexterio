"""S+3 T3 — Low volatility anomaly SP500.

Plan amendment S+3 frozen scope :
    - Univers : SP500 503 tickers (data déjà fetchée 6.5y)
    - Stratégie pré-déclarée frozen : realized vol 60d, long bottom decile, equal-weight, monthly rebal
    - Costs : 10 bps round-trip per turnover
    - Benchmarks : SPY (cap-weighted) + Equal-weight SP500 sample (same tickers)
    - Caveat documenté : survivorship bias current SP500 universe = potentiellement inflate

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

from research.label_factory import capture_summary

DATA_DIR = backend_dir / "data" / "equities"
SP500_PATH = DATA_DIR / "sp500_prices_6.5y.parquet"
F2_DIR = backend_dir / "data" / "f2_daily"

VOL_LOOKBACK_DAYS = 60
DECILE_LOW = 0  # bottom decile = lowest vol
REBAL_DAYS = 21
TC_BPS = 10.0
MIN_DECILE_SIZE = 30  # need at least 30 stocks per decile for valid rank


def load_sp500_prices() -> pd.DataFrame:
    """Load SP500 prices, filter to stocks with ≥90% data coverage (drop
    mid-period additions to avoid leading-NaN aggregation issues), forward-fill
    in-history gaps."""
    df = pd.read_parquet(SP500_PATH)
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="close").sort_index()
    coverage = pivot.notna().mean()
    valid_cols = coverage[coverage >= 0.90].index.tolist()
    print(f"  Coverage filter : {len(valid_cols)}/{pivot.shape[1]} stocks with ≥90% data")
    return pivot[valid_cols].ffill()


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


def run_low_vol_strategy(prices: pd.DataFrame, vol_lookback_days: int = VOL_LOOKBACK_DAYS,
                           rebal_days: int = REBAL_DAYS, tc_bps: float = TC_BPS,
                           equal_weight_universe: bool = False
                           ) -> tuple[pd.Series, list[dict], pd.DataFrame]:
    """Long bottom-decile realized vol, equal-weight, monthly rebalance.

    Args:
        equal_weight_universe : if True, instead of low-vol selection, equally
            weight the entire universe (used for benchmark).
    """
    n = len(prices)
    eq = pd.Series(np.nan, index=prices.index)
    cur_eq = 1.0
    cur_weights: dict[str, float] = {}
    rebal_indices = list(range(vol_lookback_days, n, rebal_days))
    tc_rate = tc_bps / 10000.0
    alloc_history = []
    per_position_perf = []

    for i in range(vol_lookback_days, n):
        date = prices.index[i]
        if i in rebal_indices:
            # Compute realized vol per stock over lookback window
            window = prices.iloc[i - vol_lookback_days:i]
            returns_window = window.pct_change().dropna()
            vols = returns_window.std()
            # Drop stocks with NaN/zero/insufficient data
            valid_vols = vols.dropna()
            valid_vols = valid_vols[valid_vols > 0]
            # Also require non-NaN current price
            valid_vols = valid_vols[~prices.iloc[i].reindex(valid_vols.index).isna()]
            if equal_weight_universe:
                # Benchmark : equal-weight all valid stocks
                if len(valid_vols) < MIN_DECILE_SIZE:
                    continue
                selected = valid_vols.index.tolist()
            else:
                if len(valid_vols) < MIN_DECILE_SIZE * 10:  # need 10 deciles worth
                    continue
                # Bottom decile = lowest vol
                threshold = valid_vols.quantile(0.10)
                selected = valid_vols[valid_vols <= threshold].index.tolist()
            if not selected:
                continue
            n_sel = len(selected)
            new_weights = {s: 1.0 / n_sel for s in selected}
            # Apply turnover cost
            all_sym = set(new_weights) | set(cur_weights)
            turnover = sum(abs(new_weights.get(s, 0) - cur_weights.get(s, 0)) for s in all_sym)
            cur_eq *= (1.0 - turnover * tc_rate)
            # Per-position 21d-forward returns for capture analysis
            for sym in selected:
                if i + rebal_days < n:
                    p_now = prices.iloc[i][sym]
                    p_fwd = prices.iloc[i + rebal_days][sym]
                    if pd.isna(p_now) or pd.isna(p_fwd) or p_now <= 0:
                        continue
                    fwd_ret = p_fwd / p_now - 1
                    hold_window = prices.iloc[i:i + rebal_days + 1][sym].dropna()
                    if hold_window.empty:
                        continue
                    peak = hold_window.max() / p_now - 1
                    trough = hold_window.min() / p_now - 1
                    per_position_perf.append({
                        "date": date,
                        "symbol": sym,
                        "realized_ret": fwd_ret,
                        "peak_ret": peak,
                        "trough_ret": trough,
                    })
            cur_weights = new_weights
            alloc_history.append({"date": date, "n_selected": n_sel,
                                    "selected_sample": selected[:5]})
        # Daily portfolio return
        if cur_weights:
            day_ret = 0.0
            for sym, w in cur_weights.items():
                p_today = prices.iloc[i][sym]
                p_prev = prices.iloc[i-1][sym]
                if pd.isna(p_today) or pd.isna(p_prev) or p_prev <= 0:
                    continue
                day_ret += w * (p_today / p_prev - 1)
            cur_eq *= (1.0 + day_ret)
        eq.iloc[i] = cur_eq

    eq = eq.dropna()
    return eq, alloc_history, pd.DataFrame(per_position_perf)


def main() -> None:
    print("=" * 100)
    print(f"S+3 T3 — Low Volatility Anomaly SP500 (bottom decile realized vol {VOL_LOOKBACK_DAYS}d, monthly rebal)")
    print("=" * 100)
    print("\nCAVEAT documenté : survivorship bias current SP500 universe (les low-vol qui ont sous-perform sont sortis de l'index)")

    prices = load_sp500_prices()
    print(f"\nData : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days, {prices.shape[1]} SP500 tickers)")

    # Strategy : low-vol bottom decile
    print(f"\nRunning low-vol bottom decile (vol_lookback={VOL_LOOKBACK_DAYS}d, monthly rebal, {TC_BPS} bps cost)...")
    eq_lv, alloc_hist, per_pos = run_low_vol_strategy(prices, equal_weight_universe=False)
    metrics_lv = _portfolio_metrics(eq_lv, "Low-Vol Bottom Decile SP500")

    # Benchmark : equal-weight SP500 sample
    print("Running equal-weight SP500 universe benchmark...")
    eq_ew, _, _ = run_low_vol_strategy(prices, equal_weight_universe=True)
    metrics_ew = _portfolio_metrics(eq_ew, "REF Equal-weight SP500 sample")

    # Benchmark : SPY (cap-weighted)
    spy = load_spy().loc[eq_lv.index[0]:eq_lv.index[-1]]
    eq_spy = spy / spy.iloc[0]
    metrics_spy = _portfolio_metrics(eq_spy, "REF SPY buy-and-hold cap-weighted")

    # Print
    print()
    print("=" * 110)
    print(f"{'Strategy':<48} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} {'vol':>6} {'%mNeg':>7}")
    print("=" * 110)
    for m in [metrics_lv, metrics_spy, metrics_ew]:
        if not m.get("valid"):
            print(f"{m['label']:<48} INVALID")
            continue
        print(f"{m['label']:<48} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
              f"{m['vol_ann_pct']:>5.1f}% {m['pct_months_neg']:>6.1f}%")

    # Capture summary
    print()
    print("=" * 100)
    print("Niveau exploitation — capture_summary per-position 21d-forward")
    print("=" * 100)
    if not per_pos.empty:
        per_pos["peak_r"] = per_pos["peak_ret"] / 0.01
        per_pos["r_multiple"] = per_pos["realized_ret"] / 0.01
        s = capture_summary(per_pos[["r_multiple", "peak_r"]].dropna())
        if s.get("n", 0) > 0:
            print(f"  n={s['n']:<6} cap_med={s['median_capture_ratio']:>+7.3f} "
                  f"%weak={s['pct_signal_weak']*100:>5.1f}% %early={s['pct_exit_early']*100:>5.1f}% "
                  f"%late={s['pct_exit_late']*100:>5.1f}% %eff={s['pct_efficient']*100:>5.1f}% "
                  f"→ {s['headline']}")

    # Sub-sample
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

    for label, eq in [("Low-Vol Bottom Decile", eq_lv), ("SPY", eq_spy),
                        ("Equal-weight SP500", eq_ew)]:
        sh1, cg1 = sub_sharpe(eq, eq.index[0], split_date)
        sh2, cg2 = sub_sharpe(eq, split_date, eq.index[-1])
        print(f"  {label:<35} 2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}%  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}%  | ΔSharpe={sh2-sh1:>+5.2f}")

    # Gate
    print()
    print("=" * 100)
    print("Gate plan S+3 T3")
    print("=" * 100)
    sh = metrics_lv["Sharpe_ann"]
    cal = metrics_lv["Calmar"]
    sh_spy = metrics_spy["Sharpe_ann"]
    sh_ew = metrics_ew["Sharpe_ann"]
    cal_spy = metrics_spy["Calmar"]
    cal_ew = metrics_ew["Calmar"]
    print(f"  Low-Vol Sharpe ≥ 0.8 : {'PASS' if sh >= 0.8 else 'FAIL'} (got {sh:.2f})")
    print(f"  Low-Vol Sharpe ≥ 0.5 (kill rule) : {'OK' if sh >= 0.5 else 'KILL'} (got {sh:.2f})")
    print(f"  Low-Vol Calmar > best bench ({max(cal_spy, cal_ew):.2f}) : "
          f"{'PASS' if cal > max(cal_spy, cal_ew) else 'FAIL'} (got {cal:.2f})")
    print(f"  Low-Vol Sharpe > best bench ({max(sh_spy, sh_ew):.2f}) : "
          f"{'PASS' if sh > max(sh_spy, sh_ew) else 'FAIL'} (got {sh:.2f})")

    # Save
    out_dir = backend_dir / "results" / "s3_t3_low_vol"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "low_vol_decile": eq_lv,
        "SPY": eq_spy.reindex(eq_lv.index),
        "equal_weight_sp500": eq_ew.reindex(eq_lv.index),
    }).to_parquet(out_dir / "equity_curves.parquet")
    if not per_pos.empty:
        per_pos.to_parquet(out_dir / "per_position_perf.parquet", index=False)
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
