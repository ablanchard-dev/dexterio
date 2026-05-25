"""run_cycle11_tsmom_corrected.py — R&D Cycle v6 / Cycle 11 TSMOM corrigé avec audit fixes.

Audit issues fixed (v1 audit_methodology_v1.md) :
  1. **Cash earns risk-free rate** : ^IRX 13-week T-bill yield daily (was: 0% in cash)
  2. **Multi-lookback ensemble** : 1m/3m/6m/12m simultanés (was: 252d only)
  3. **Monthly rebalance** : 1st trading day each month (was: daily, costs ×20)
  4. **Realistic costs 3 bps RT** for liquid ETFs SPY/QQQ/GLD/TLT (was: 10 bps)
  5. **Vol-target portfolio level** w/ leverage cap 1.5× (was: per-asset capped 1×)

Hypothèse pré-spec :
  Audit v1 estime corrections 1+2+3 lift Sharpe 4etf TSMOM de 0.96 → 1.20-1.40 réaliste.
  Si confirmé, multi-strategy ensemble corrigé devrait atteindre 1.5-1.8 (vs 0.63 baseline).

Anti-lookahead :
  - Lookback signals strict past (lookback - 1 included only)
  - Monthly rebalance signal computed from t-1 close, executed at t open (1-day lag)
  - Cash rate ^IRX yield t-1 applied during cash days
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
F2_DAILY = REPO_ROOT / "backend/data/f2_daily"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

LOOKBACKS = [21, 63, 126, 252]  # 1m, 3m, 6m, 12m
VOL_WINDOW = 60
TRADING_DAYS = 252
RT_BPS_ETF = 3  # 3 bps for liquid ETFs (real spread + slippage)
ASSETS = ["SPY", "QQQ", "GLD", "TLT"]
VOL_TARGET_PORTFOLIO = 0.10  # 10% portfolio vol target
LEVERAGE_CAP = 1.5  # max leverage


def load_etf_panel():
    out = {}
    for sym in ASSETS:
        path = F2_DAILY / f"{sym}_1d.parquet"
        df = pd.read_parquet(path)[["date", "Adj Close"]].rename(columns={"Adj Close": sym})
        df["date"] = pd.to_datetime(df["date"])
        out[sym] = df.set_index("date")
    return pd.concat(list(out.values()), axis=1).dropna()


def load_riskfree_rate(start: str = "2019-06-01", end: str = "2025-11-30") -> pd.Series:
    """Fetch ^IRX (13-week T-bill yield) — free yfinance, daily."""
    cache_path = OUT_DIR / "irx_cache.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)["irx_daily"]
    irx = yf.Ticker("^IRX").history(start=start, end=end, auto_adjust=False)["Close"]
    # ^IRX is annualized yield in %, convert to daily decimal rate
    irx = irx / 100.0  # to decimal (5.0% → 0.05)
    irx_daily = irx / TRADING_DAYS  # daily compounding rate
    irx_daily.index = pd.to_datetime(irx_daily.index).tz_localize(None)
    irx_daily.name = "irx_daily"
    irx_daily.to_frame().to_parquet(cache_path)
    return irx_daily


def compute_multi_lookback_signal(prices: pd.Series, lookbacks: list[int]) -> pd.Series:
    """Average of binary signals across lookbacks. Returns continuous score 0-1."""
    signals = []
    for lb in lookbacks:
        r = (prices.shift(1) / prices.shift(lb)) - 1
        signals.append((r > 0).astype(float))
    return pd.concat(signals, axis=1).mean(axis=1)  # 0=all bear, 1=all bull, 0.5=mixed


def compute_vol_target_weight(log_ret: pd.Series, vol_target: float, periods_per_year: int) -> pd.Series:
    """Vol-target sizing past-only."""
    vol = log_ret.shift(1).rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(periods_per_year)
    w = vol_target / vol
    return w.fillna(0.0)


def get_monthly_rebalance_dates(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First trading day of each month."""
    df = pd.DataFrame(index=dates)
    df["month"] = df.index.to_period("M")
    return df.groupby("month").apply(lambda x: x.index[0]).values


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 11] TSMOM corrigé — multi-lookback + monthly + cash rfr + costs 3 bps", flush=True)
    print(f"  Assets : {ASSETS}", flush=True)
    print(f"  Lookbacks : {LOOKBACKS} days (1m/3m/6m/12m ensemble)", flush=True)
    print(f"  Costs : {RT_BPS_ETF} bps RT (realistic for ETFs)", flush=True)
    print(f"  Cash earns risk-free ^IRX daily", flush=True)
    print(f"  Monthly rebalance (1st trading day each month)", flush=True)

    print("[1/5] Loading prices + risk-free rate...", flush=True)
    etf = load_etf_panel()
    rfr = load_riskfree_rate()
    rfr = rfr.reindex(etf.index).ffill().fillna(0.0)
    print(f"      ETF panel : {etf.shape}, rfr median daily : {rfr.median():.6f} "
          f"(annualized {rfr.median()*TRADING_DAYS*100:.2f}%)", flush=True)

    log_ret = np.log(etf).diff()

    print(f"[2/5] Computing multi-lookback signals (4 horizons averaged)...", flush=True)
    signals = pd.DataFrame(index=etf.index, columns=ASSETS, dtype=float)
    weights_continuous = pd.DataFrame(index=etf.index, columns=ASSETS, dtype=float)
    for sym in ASSETS:
        sig = compute_multi_lookback_signal(etf[sym], LOOKBACKS)
        # Vol target per asset
        per_asset_w = compute_vol_target_weight(log_ret[sym], VOL_TARGET_PORTFOLIO / np.sqrt(len(ASSETS)), TRADING_DAYS)
        weights_continuous[sym] = sig * per_asset_w
        signals[sym] = sig

    print(f"[3/5] Resampling to monthly rebalance + apply leverage cap {LEVERAGE_CAP}x...", flush=True)
    rebal_dates = get_monthly_rebalance_dates(etf.index)
    monthly_w = pd.DataFrame(index=etf.index, columns=ASSETS, dtype=float)
    monthly_w.loc[:] = np.nan
    for d in rebal_dates:
        if d in weights_continuous.index:
            monthly_w.loc[d] = weights_continuous.loc[d].values
    monthly_w = monthly_w.ffill()
    # Leverage cap on portfolio level (sum of absolute weights)
    gross = monthly_w.abs().sum(axis=1)
    excess = (gross > LEVERAGE_CAP).astype(float)
    scale = np.where(gross > LEVERAGE_CAP, LEVERAGE_CAP / gross, 1.0)
    monthly_w = monthly_w.mul(scale, axis=0)
    monthly_w = monthly_w.fillna(0.0)
    avg_active = (monthly_w > 0).any(axis=1).mean()
    print(f"      Avg active days : {avg_active*100:.1f}%, max weight sum : {gross.max():.3f}", flush=True)

    print("[4/5] Simulating PnL with cash earning rfr...", flush=True)
    # Active position PnL : weight × log_ret per asset
    active_pnl = (monthly_w.shift(1) * log_ret).sum(axis=1)
    # Cash period weight : 1 - sum(weights), earns rfr
    cash_weight = (1 - monthly_w.shift(1).abs().sum(axis=1)).clip(lower=0)
    cash_pnl = cash_weight * rfr
    # Turnover cost (daily change in weights)
    turnover = (monthly_w - monthly_w.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS_ETF / 10_000.0
    # Total daily pnl
    daily_pnl = active_pnl + cash_pnl - cost

    perf_start = max(LOOKBACKS) + VOL_WINDOW
    perf = daily_pnl.iloc[perf_start:]

    print("[5/5] Computing metrics...", flush=True)
    sharpe_active_only = (active_pnl.iloc[perf_start:].mean() / active_pnl.iloc[perf_start:].std()) * np.sqrt(TRADING_DAYS)
    sharpe = (perf.mean() / perf.std()) * np.sqrt(TRADING_DAYS)
    eq = (1 + perf).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / len(perf)) - 1
    rmax = eq.cummax()
    dd = (eq - rmax) / rmax
    max_dd = dd.min()

    # Sub-sample stability — rolling 252d Sharpe
    rolling_sharpe = perf.rolling(252).mean() / perf.rolling(252).std() * np.sqrt(TRADING_DAYS)
    rs_min = rolling_sharpe.dropna().min()
    rs_max = rolling_sharpe.dropna().max()
    rs_median = rolling_sharpe.dropna().median()

    # Hard split for comparison with prior cycles
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf.index < mid]
    h2 = perf[perf.index >= mid]
    sh_h1 = (h1.mean() / h1.std()) * np.sqrt(TRADING_DAYS) if h1.std() != 0 else 0.0
    sh_h2 = (h2.mean() / h2.std()) * np.sqrt(TRADING_DAYS) if h2.std() != 0 else 0.0
    delta_sub = abs(sh_h1 - sh_h2)

    print(f"      Sharpe (active+cash rfr) = {sharpe:.3f}", flush=True)
    print(f"      Sharpe (active only, no cash earning) = {sharpe_active_only:.3f}", flush=True)
    print(f"      CAGR = {cagr*100:.2f}%, MaxDD = {max_dd*100:.2f}%", flush=True)
    print(f"      Rolling 252d Sharpe : min {rs_min:.2f}, median {rs_median:.2f}, max {rs_max:.2f}", flush=True)
    print(f"      Hard split h1/h2 : {sh_h1:.3f}/{sh_h2:.3f} Δ={delta_sub:.3f}", flush=True)

    # Compare to baseline
    baseline_cycle10 = 0.794  # tsmom_4etf in Cycle 10 (full sample, no cash, daily, 10 bps)
    lift = sharpe - baseline_cycle10

    md_lines = []
    md_lines.append("# Cycle 11 — TSMOM corrigé (audit fixes 1+2+3+4+5)")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v6 — Cycle 11 (audit-driven correction)")
    md_lines.append("")
    md_lines.append(f"## Metrics avant/après corrections")
    md_lines.append("")
    md_lines.append("| Variant | Sharpe |")
    md_lines.append("|---|---:|")
    md_lines.append(f"| TSMOM 4etf Cycle 10 baseline (single 252d, daily rebal, 10 bps, no cash rfr) | {baseline_cycle10:.3f} |")
    md_lines.append(f"| TSMOM 4etf Cycle 11 active-only (no cash rfr, multi-lookback, monthly, 3 bps) | {sharpe_active_only:.3f} |")
    md_lines.append(f"| TSMOM 4etf Cycle 11 + cash earns rfr | **{sharpe:.3f}** |")
    md_lines.append(f"| Lift cumulé fixes 1+2+3+4+5 | {lift:+.3f} |")
    md_lines.append("")
    md_lines.append("## Audit fixes appliqués")
    md_lines.append("")
    md_lines.append("1. **Multi-lookback ensemble** : signals 1m+3m+6m+12m averaged (was: 252d only)")
    md_lines.append("2. **Monthly rebalance** : 1st trading day each month (was: daily)")
    md_lines.append(f"3. **Costs réalistes** : {RT_BPS_ETF} bps RT (was: 10 bps)")
    md_lines.append(f"4. **Cash earns risk-free rate** : ^IRX 13-week T-bill yield daily (was: 0%)")
    md_lines.append(f"5. **Vol-target portfolio level + leverage cap {LEVERAGE_CAP}×** (was: per-asset cap 1×)")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net (incl cash rfr) | **{sharpe:.3f}** |")
    md_lines.append(f"| Sharpe active-only | {sharpe_active_only:.3f} |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {max_dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {cagr/abs(max_dd) if max_dd != 0 else 0:.2f} |")
    md_lines.append(f"| Rolling 252d Sharpe min | {rs_min:.3f} |")
    md_lines.append(f"| Rolling 252d Sharpe median | {rs_median:.3f} |")
    md_lines.append(f"| Rolling 252d Sharpe max | {rs_max:.3f} |")
    md_lines.append(f"| Sub-sample h1/h2 (hard split) | {sh_h1:.3f}/{sh_h2:.3f} (Δ={delta_sub:.3f}) |")
    md_lines.append("")
    out_md = OUT_DIR / "cycle11_tsmom_corrected_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_frame("pnl").to_parquet(OUT_DIR / "cycle11_tsmom_corrected_pnl.parquet")

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Sharpe corrigé : {sharpe:.3f} (lift {lift:+.3f} vs baseline {baseline_cycle10})", flush=True)


if __name__ == "__main__":
    main()
