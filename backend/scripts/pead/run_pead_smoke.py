"""S+2 J1 — PEAD smoke (Post-Earnings Announcement Drift, Bernard & Thomas 1989/1990).

3 variantes pré-déclarées strictes (frozen, plan v4.0 amendment S+2) :
    V1 : long top-decile EPS surprise per quarterly cohort, hold 60 trading days
    V2 : V1 + filter market cap > $5B (proxy via avg dollar volume top quartile)
    V3 : long-short top decile vs bottom decile (market neutral)

Entry : T+1 next trading day open after earnings_date
Exit : T+60 trading days close (fixed hold, no SL/TP — academic standard)
Equal-weight portfolio of active positions, daily marked-to-market

Costs simulés : 10 bps round-trip per entry+exit (commission + spread retail)

Métriques niveau système : Sharpe net, CAGR, max DD, n_events, vs SP500 ref
Métriques niveau exploitation : capture_summary (median_capture_ratio, % weak/early/late)
Sub-sample stability : 2019-2022 vs 2022-2025
Permutation 500 iter SI pas clean fail

Usage : python backend/scripts/pead/run_pead_smoke.py
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

DATA_DIR = backend_dir / "data"
PRICES_PATH = DATA_DIR / "equities" / "sp500_prices_6.5y.parquet"
EARNINGS_PATH = DATA_DIR / "earnings" / "sp500_earnings_6.5y.parquet"

HOLD_DAYS = 60          # academic standard PEAD hold
COST_BPS_RT = 10.0      # 10 bps round-trip (5 bps each side)
DECILE_TOP = 9          # top decile = label 9 (10 deciles 0-9)
DECILE_BOTTOM = 0       # bottom decile = label 0
MIN_EVENTS_PER_QUARTER = 30  # need enough cohort to rank into deciles


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PRICES_PATH.exists():
        raise FileNotFoundError(f"Prices not found: {PRICES_PATH}")
    if not EARNINGS_PATH.exists():
        raise FileNotFoundError(f"Earnings not found: {EARNINGS_PATH}")
    prices = pd.read_parquet(PRICES_PATH)
    earnings = pd.read_parquet(EARNINGS_PATH)
    prices["date"] = pd.to_datetime(prices["date"])
    earnings["earnings_date"] = pd.to_datetime(earnings["earnings_date"])
    return prices, earnings


def compute_event_returns(events: pd.DataFrame, prices: pd.DataFrame,
                            hold_days: int = HOLD_DAYS) -> pd.DataFrame:
    """For each earnings event, compute T+1 entry → T+hold exit return.

    Returns DataFrame with : symbol, earnings_date, surprise_pct,
    entry_date, exit_date, realized_ret, peak_ret, mae_ret, n_active_days.
    """
    # Build per-symbol price index (sorted)
    prices_sorted = prices.sort_values(["symbol", "date"]).reset_index(drop=True)
    prices_by_sym = {sym: g.reset_index(drop=True) for sym, g in prices_sorted.groupby("symbol")}

    records = []
    for _, ev in events.iterrows():
        sym = ev["symbol"]
        ed = ev["earnings_date"]
        sub = prices_by_sym.get(sym)
        if sub is None or sub.empty:
            continue
        # Find first trading day strictly after earnings_date
        post = sub[sub["date"] > ed]
        if len(post) < hold_days + 1:
            continue
        entry_row = post.iloc[0]
        exit_row = post.iloc[hold_days]
        entry_open = entry_row["open"]
        exit_close = exit_row["close"]
        if pd.isna(entry_open) or pd.isna(exit_close) or entry_open <= 0:
            continue
        # Peak / trough within hold window (exclude entry day open itself)
        window = post.iloc[1:hold_days + 1]
        if window.empty:
            continue
        peak_close = window["close"].max()
        trough_close = window["close"].min()
        if pd.isna(peak_close) or pd.isna(trough_close):
            continue
        realized_ret = exit_close / entry_open - 1
        peak_ret = peak_close / entry_open - 1
        mae_ret = trough_close / entry_open - 1
        records.append({
            "symbol": sym,
            "earnings_date": ed,
            "surprise_pct": ev.get("surprise_pct", np.nan),
            "eps_actual": ev.get("eps_actual", np.nan),
            "eps_estimate": ev.get("eps_estimate", np.nan),
            "entry_date": entry_row["date"],
            "exit_date": exit_row["date"],
            "entry_open": float(entry_open),
            "exit_close": float(exit_close),
            "realized_ret": float(realized_ret),
            "peak_ret": float(peak_ret),
            "mae_ret": float(mae_ret),
        })
    return pd.DataFrame(records)


def assign_deciles(events_with_returns: pd.DataFrame, by: str = "earnings_date",
                    quarter_freq: str = "Q") -> pd.DataFrame:
    """Assign decile rank per quarterly cohort based on surprise_pct."""
    df = events_with_returns.copy()
    df["quarter"] = df[by].dt.to_period(quarter_freq)
    # Filter quarters with enough events for ranking
    cohort_sizes = df.groupby("quarter").size()
    valid_quarters = cohort_sizes[cohort_sizes >= MIN_EVENTS_PER_QUARTER].index
    df = df[df["quarter"].isin(valid_quarters)]
    df["decile"] = df.groupby("quarter")["surprise_pct"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=False, duplicates="drop")
    )
    return df


def apply_costs_to_returns(returns: pd.Series, cost_bps_rt: float = COST_BPS_RT) -> pd.Series:
    """Apply round-trip costs to per-event returns."""
    cost = cost_bps_rt / 10000.0
    return returns - cost


def build_portfolio_daily_returns(events_df: pd.DataFrame, prices: pd.DataFrame,
                                    hold_days: int = HOLD_DAYS,
                                    direction: int = 1) -> pd.Series:
    """Convert per-event signals into daily portfolio return series.

    Each day, equal-weight all currently-active positions.
    direction = +1 (long) or -1 (short).
    """
    if events_df.empty:
        return pd.Series(dtype=float)

    # Build prices index for faster lookup
    prices_sorted = prices.sort_values(["symbol", "date"]).reset_index(drop=True)
    prices_by_sym = {sym: g.set_index("date")["close"]
                     for sym, g in prices_sorted.groupby("symbol")}

    # For each event, compute daily returns over hold window
    # Then aggregate equal-weight across overlapping events
    daily_position_returns = {}  # date → list of (sym, daily_ret)

    for _, ev in events_df.iterrows():
        sym = ev["symbol"]
        sym_prices = prices_by_sym.get(sym)
        if sym_prices is None:
            continue
        entry_date = ev["entry_date"]
        # Window : entry_date+1 to exit_date (inclusive)
        window_dates = sym_prices[(sym_prices.index >= entry_date) &
                                    (sym_prices.index <= ev["exit_date"])]
        if len(window_dates) < 2:
            continue
        # Daily returns within window
        daily_rets = window_dates.pct_change().dropna()
        for d, r in daily_rets.items():
            daily_position_returns.setdefault(d, []).append(r * direction)

    # Aggregate equal-weight per day
    sorted_dates = sorted(daily_position_returns.keys())
    portfolio_rets = pd.Series(
        [np.mean(daily_position_returns[d]) for d in sorted_dates],
        index=pd.DatetimeIndex(sorted_dates),
        name="portfolio_ret"
    )
    return portfolio_rets


def compute_metrics(returns: pd.Series, label: str) -> dict:
    if len(returns) < 5:
        return {"label": label, "n_days": len(returns), "valid": False}
    eq = (1 + returns).cumprod()
    days = (eq.index[-1] - eq.index[0]).days
    years = days / 365.25
    final_ret = eq.iloc[-1] - 1
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
    rm = eq.expanding().max()
    dd = (eq / rm - 1).min()
    return {
        "label": label,
        "n_days": len(returns),
        "total_return_pct": final_ret * 100,
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": sharpe,
        "max_DD_pct": dd * 100,
        "vol_ann_pct": returns.std() * np.sqrt(252) * 100,
        "valid": True,
    }


def event_capture_summary(events_df: pd.DataFrame, direction: int = 1) -> dict:
    """Per-event capture analysis using R = 1% convention.

    For long (direction=+1) : peak_R = peak_ret/0.01, realized_R = realized_ret/0.01
    For short (direction=-1) : invert signs (long-equivalent return = -realized_ret)
    """
    if events_df.empty:
        return {"n": 0, "headline": "no_events"}
    df = events_df.copy()
    if direction == 1:
        df["peak_r"] = df["peak_ret"] / 0.01
        df["r_multiple"] = df["realized_ret"] / 0.01
    else:
        df["peak_r"] = -df["mae_ret"] / 0.01  # short profit = price drops
        df["r_multiple"] = -df["realized_ret"] / 0.01
    return capture_summary(df[["r_multiple", "peak_r"]].dropna())


def main() -> None:
    print("=" * 100)
    print("S+2 J1 PEAD SMOKE — Post-Earnings Announcement Drift on SP500 6.5y")
    print("=" * 100)

    prices, earnings = load_data()
    print(f"\nData loaded :")
    print(f"  Prices : {len(prices):,} rows, {prices['symbol'].nunique()} symbols, "
          f"{prices['date'].min().date()} → {prices['date'].max().date()}")
    print(f"  Earnings : {len(earnings):,} events, {earnings['symbol'].nunique()} symbols, "
          f"{earnings['earnings_date'].min().date()} → {earnings['earnings_date'].max().date()}")

    # Filter earnings : need both estimate and actual (no future events)
    earnings_clean = earnings.dropna(subset=["eps_actual", "eps_estimate"]).copy()
    earnings_clean = earnings_clean[earnings_clean["eps_estimate"].abs() > 0.01]
    # Recompute surprise_pct cleanly
    earnings_clean["surprise_pct"] = (
        (earnings_clean["eps_actual"] - earnings_clean["eps_estimate"])
        / earnings_clean["eps_estimate"].abs() * 100
    )
    # Drop extreme outliers (>1000% surprise = data error)
    earnings_clean = earnings_clean[earnings_clean["surprise_pct"].abs() < 1000]
    print(f"  Earnings clean : {len(earnings_clean):,} events post-filter")

    # Compute event returns
    print("\nComputing per-event T+1 → T+60 returns...")
    event_rets = compute_event_returns(earnings_clean, prices, hold_days=HOLD_DAYS)
    print(f"  {len(event_rets):,} events with valid 60d hold window")
    print(f"  Mean realized return all events : {event_rets['realized_ret'].mean()*100:+.2f}%")
    print(f"  Date range entries : {event_rets['entry_date'].min().date()} → "
          f"{event_rets['entry_date'].max().date()}")

    # Assign deciles per quarterly cohort
    event_rets_decile = assign_deciles(event_rets)
    print(f"\nQuarterly cohorts ranked into deciles : {event_rets_decile['quarter'].nunique()} quarters")
    print(f"  Mean events per quarter : {event_rets_decile.groupby('quarter').size().mean():.0f}")

    # ===== V1 : long top decile =====
    v1_events = event_rets_decile[event_rets_decile["decile"] == DECILE_TOP].copy()
    print(f"\n=== V1 long top-decile : n={len(v1_events)} events ===")
    print(f"  Mean surprise_pct : {v1_events['surprise_pct'].mean():+.2f}%")
    print(f"  Mean realized_ret : {v1_events['realized_ret'].mean()*100:+.2f}%")
    v1_portfolio = build_portfolio_daily_returns(v1_events, prices, direction=1)
    v1_portfolio_net = apply_costs_to_returns(v1_portfolio, COST_BPS_RT)
    v1_metrics = compute_metrics(v1_portfolio_net, "V1 long top-decile")

    # ===== V2 : V1 + filter market cap proxy via avg dollar volume top half =====
    # Compute avg dollar volume per symbol over data period
    prices_sym = prices.copy()
    prices_sym["dollar_vol"] = prices_sym["close"] * prices_sym["volume"]
    avg_dvol = prices_sym.groupby("symbol")["dollar_vol"].mean()
    median_dvol = avg_dvol.median()
    big_caps = avg_dvol[avg_dvol > median_dvol].index.tolist()
    v2_events = v1_events[v1_events["symbol"].isin(big_caps)].copy()
    print(f"\n=== V2 long top-decile + big_caps (avg_dvol > median ${median_dvol/1e6:.0f}M) : n={len(v2_events)} events ===")
    print(f"  Mean realized_ret : {v2_events['realized_ret'].mean()*100:+.2f}%")
    v2_portfolio = build_portfolio_daily_returns(v2_events, prices, direction=1)
    v2_portfolio_net = apply_costs_to_returns(v2_portfolio, COST_BPS_RT)
    v2_metrics = compute_metrics(v2_portfolio_net, "V2 top-decile + big_caps")

    # ===== V3 : long top decile - short bottom decile =====
    v3_long = v1_events
    v3_short = event_rets_decile[event_rets_decile["decile"] == DECILE_BOTTOM].copy()
    print(f"\n=== V3 long top - short bottom : n_long={len(v3_long)}, n_short={len(v3_short)} ===")
    print(f"  Mean realized_ret long : {v3_long['realized_ret'].mean()*100:+.2f}%")
    print(f"  Mean realized_ret short : {v3_short['realized_ret'].mean()*100:+.2f}%")
    v3_long_portfolio = build_portfolio_daily_returns(v3_long, prices, direction=1)
    v3_short_portfolio = build_portfolio_daily_returns(v3_short, prices, direction=-1)
    # Combine : equal-weight long and short
    common_dates = v3_long_portfolio.index.intersection(v3_short_portfolio.index)
    v3_portfolio = (v3_long_portfolio.loc[common_dates] + v3_short_portfolio.loc[common_dates]) / 2
    v3_portfolio_net = apply_costs_to_returns(v3_portfolio, COST_BPS_RT)
    v3_metrics = compute_metrics(v3_portfolio_net, "V3 long-short (market neutral)")

    # SPY reference
    spy_prices = prices[prices["symbol"] == "AAPL"].sort_values("date")  # placeholder
    # Better : use SPY directly from f2_daily
    f2_dir = backend_dir / "data" / "f2_daily"
    spy_path = f2_dir / "SPY_1d.parquet"
    if spy_path.exists():
        spy = pd.read_parquet(spy_path)
        spy["date"] = pd.to_datetime(spy["date"])
        spy_full = spy.set_index("date")["Close"]
    else:
        spy_full = None

    # Print results
    print()
    print("=" * 100)
    print(f"{'Variant':<55} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'n_days':>8}")
    print("=" * 100)
    for m in [v1_metrics, v2_metrics, v3_metrics]:
        if not m.get("valid"):
            print(f"{m['label']:<55} INVALID (n_days={m['n_days']})")
            continue
        print(f"{m['label']:<55} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['n_days']:>8}")

    if spy_full is not None:
        # Restrict SPY to overlap with V1 portfolio dates
        if v1_portfolio_net.index.size > 0:
            spy_window = spy_full.loc[v1_portfolio_net.index[0]:v1_portfolio_net.index[-1]]
            spy_ret = spy_window.pct_change().dropna()
            spy_eq = (1 + spy_ret).cumprod()
            years = (spy_window.index[-1] - spy_window.index[0]).days / 365.25
            spy_cagr = spy_eq.iloc[-1] ** (1/years) - 1 if years > 0 else 0
            spy_sharpe = spy_ret.mean() / spy_ret.std() * np.sqrt(252)
            rm_spy = spy_eq.expanding().max()
            spy_dd = (spy_eq / rm_spy - 1).min()
            print(f"{'REF SPY buy-and-hold same window':<55} {spy_cagr*100:>6.2f}% "
                  f"{spy_sharpe:>+7.2f} {spy_dd*100:>+7.1f}% {len(spy_ret):>8}")

    # Capture summary per variant (event-level)
    print()
    print("=" * 100)
    print("Niveau exploitation — capture_summary per variant (event-level R=1% convention)")
    print("=" * 100)
    for label, evs, direction in [
        ("V1 long top-decile", v1_events, 1),
        ("V2 top-decile + big_caps", v2_events, 1),
        ("V3 long-side (top-decile)", v3_long, 1),
        ("V3 short-side (bottom-decile)", v3_short, -1),
    ]:
        s = event_capture_summary(evs, direction=direction)
        if s.get("n", 0) == 0:
            print(f"  {label:<35} no events")
            continue
        print(f"  {label:<35} n={s['n']:<5} cap_med={s['median_capture_ratio']:>+7.3f} "
              f"%weak={s['pct_signal_weak']*100:>5.1f}% %early={s['pct_exit_early']*100:>5.1f}% "
              f"%late={s['pct_exit_late']*100:>5.1f}% %eff={s['pct_efficient']*100:>5.1f}% "
              f"→ {s['headline']}")

    # Sub-sample stability 2019-2022 vs 2022-2025
    print()
    print("=" * 100)
    print("Sub-sample stability — 2019-2022 vs 2022-2025")
    print("=" * 100)
    split_date = pd.Timestamp("2022-06-01")

    def sub(ret: pd.Series, start, end) -> tuple[float, float, int]:
        r = ret.loc[start:end].dropna()
        if len(r) < 5 or r.std() == 0:
            return 0.0, 0.0, len(r)
        sh = r.mean() / r.std() * np.sqrt(252)
        eq = (1 + r).cumprod()
        ye = (r.index[-1] - r.index[0]).days / 365.25
        cg = eq.iloc[-1] ** (1/ye) - 1 if ye > 0 else 0
        return float(sh), float(cg * 100), len(r)

    for label, port in [("V1", v1_portfolio_net), ("V2", v2_portfolio_net), ("V3", v3_portfolio_net)]:
        if port.empty:
            continue
        sh1, cg1, n1 = sub(port, port.index[0], split_date)
        sh2, cg2, n2 = sub(port, split_date, port.index[-1])
        print(f"  {label}  2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}% n={n1}  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}% n={n2}  | "
              f"ΔSharpe={sh2-sh1:>+5.2f}")

    # Gate evaluation
    print()
    print("=" * 100)
    print("Gate plan S+2 PEAD")
    print("=" * 100)
    for m in [v1_metrics, v2_metrics, v3_metrics]:
        if not m.get("valid"):
            continue
        print(f"\n  {m['label']} :")
        print(f"    Sharpe ≥ 0.8 (PASS bar)   : "
              f"{'PASS' if m['Sharpe_ann'] >= 0.8 else 'FAIL'} (got {m['Sharpe_ann']:.2f})")
        print(f"    Sharpe ≥ 0.5 (kill rule)  : "
              f"{'OK' if m['Sharpe_ann'] >= 0.5 else 'KILL'} (got {m['Sharpe_ann']:.2f})")
        print(f"    max DD ≥ -20%             : "
              f"{'PASS' if m['max_DD_pct'] >= -20 else 'FAIL'} (got {m['max_DD_pct']:.1f}%)")

    # Save trades + portfolio for further analysis
    out_dir = backend_dir / "results" / "pead"
    out_dir.mkdir(parents=True, exist_ok=True)
    v1_events.to_parquet(out_dir / "v1_events.parquet", index=False)
    v3_short.to_parquet(out_dir / "v3_short_events.parquet", index=False)
    v1_portfolio_net.to_frame("ret").to_parquet(out_dir / "v1_portfolio_returns.parquet")
    v2_portfolio_net.to_frame("ret").to_parquet(out_dir / "v2_portfolio_returns.parquet")
    v3_portfolio_net.to_frame("ret").to_parquet(out_dir / "v3_portfolio_returns.parquet")
    print(f"\n[saved trades + portfolio returns to {out_dir}]")


if __name__ == "__main__":
    main()
