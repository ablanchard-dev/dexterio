"""run_cycle12_tsmom_extended_universe.py — R&D Cycle v6 / Cycle 12 TSMOM extended universe.

Audit-driven fixes applied (from AUDIT_methodology_v1.md) + universe expansion :
  - Multi-lookback ensemble [63d, 126d, 252d] (3m/6m/12m), drop 21d trop noisy
  - Monthly rebalance (1st trading day each month)
  - Costs 3 bps RT
  - Cash earns ^IRX risk-free rate
  - Vol-target portfolio level + leverage cap 1.5×
  - **Universe étendu 14 assets** : SPY, QQQ, IWM (equity US lg/sm), EFA (intl dev), EEM, FXI (emerging),
    TLT (bonds), GLD, SLV (precious), USO (oil), DBA (agriculture), UUP (USD), FXY (JPY), FXE (EUR)

Hypothèse pré-spec :
  Universe diversification cross-asset class = correlations plus basses → portfolio Sharpe lift.
  14 assets avec ρ_avg attendu 0.15-0.25 (vs 0.30+ avec 4 ETFs concentrés US) →
  ceiling théorique Sharpe individuel × √(N/(1+(N-1)×ρ)) significativement plus haut.
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
CACHE_DIR = REPO_ROOT / "backend/data/multi_asset"

LOOKBACKS = [63, 126, 252]  # 3m, 6m, 12m (drop 21d as too noisy)
VOL_WINDOW = 60
TRADING_DAYS = 252
RT_BPS_ETF = 3
VOL_TARGET_PORT = 0.12  # 12% portfolio
LEVERAGE_CAP = 1.5
ASSETS = {
    "SPY": "equity_us_lg",
    "QQQ": "equity_us_lg",
    "IWM": "equity_us_sm",
    "EFA": "equity_intl_dev",
    "EEM": "equity_intl_em",
    "FXI": "equity_intl_em",
    "TLT": "bonds",
    "GLD": "commodity_precious",
    "SLV": "commodity_precious",
    "USO": "commodity_oil",
    "DBA": "commodity_agri",
    "UUP": "fx_usd",
    "FXY": "fx_jpy",
    "FXE": "fx_eur",
}


def load_assets():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "extended_14assets.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    rows = []
    for sym in ASSETS.keys():
        df = yf.Ticker(sym).history(start="2019-06-01", end="2025-11-30", auto_adjust=False)
        s = df["Adj Close"].rename(sym)
        rows.append(s)
    out = pd.concat(rows, axis=1)
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out.index.name = "date"
    out.to_parquet(cache)
    return out


def load_irx():
    cache_path = OUT_DIR / "irx_cache.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)["irx_daily"]
    irx = yf.Ticker("^IRX").history(start="2019-06-01", end="2025-11-30")["Close"] / 100.0 / TRADING_DAYS
    irx.index = pd.to_datetime(irx.index).tz_localize(None)
    return irx.rename("irx_daily")


def compute_multi_lookback_signal(prices: pd.Series, lookbacks: list[int]) -> pd.Series:
    sigs = []
    for lb in lookbacks:
        r = (prices.shift(1) / prices.shift(lb)) - 1
        sigs.append((r > 0).astype(float))
    return pd.concat(sigs, axis=1).mean(axis=1)


def compute_vol_target_weight(log_ret: pd.Series, vol_target: float) -> pd.Series:
    vol = log_ret.shift(1).rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(TRADING_DAYS)
    w = vol_target / vol
    return w.fillna(0.0)


def get_monthly_rebalance_dates(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    df = pd.DataFrame(index=dates)
    df["month"] = df.index.to_period("M")
    return [g.index[0] for _, g in df.groupby("month")]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 12] TSMOM 14-asset extended universe (corrections + diversification)", flush=True)
    print(f"  Universe : {list(ASSETS.keys())} ({len(ASSETS)} assets, {len(set(ASSETS.values()))} categories)",
          flush=True)
    print(f"  Lookbacks : {LOOKBACKS}d (3m/6m/12m ensemble, no 21d)", flush=True)
    print(f"  Costs : {RT_BPS_ETF} bps RT", flush=True)

    print("[1/5] Loading 14-asset panel + ^IRX risk-free rate...", flush=True)
    panel = load_assets().dropna()
    rfr = load_irx().reindex(panel.index).ffill().fillna(0.0)
    print(f"      Panel : {panel.shape}", flush=True)

    log_ret = np.log(panel).diff()

    print("[2/5] Multi-lookback signals + per-asset vol-target...", flush=True)
    weights_continuous = pd.DataFrame(index=panel.index, columns=panel.columns, dtype=float)
    for sym in panel.columns:
        sig = compute_multi_lookback_signal(panel[sym], LOOKBACKS)
        per_asset_target = VOL_TARGET_PORT / np.sqrt(len(panel.columns))
        per_asset_w = compute_vol_target_weight(log_ret[sym], per_asset_target)
        weights_continuous[sym] = sig * per_asset_w

    print(f"[3/5] Monthly rebalance + leverage cap {LEVERAGE_CAP}×...", flush=True)
    rebal = get_monthly_rebalance_dates(panel.index)
    monthly_w = pd.DataFrame(np.nan, index=panel.index, columns=panel.columns)
    for d in rebal:
        if d in weights_continuous.index:
            monthly_w.loc[d] = weights_continuous.loc[d].values
    monthly_w = monthly_w.ffill().fillna(0.0)
    gross = monthly_w.abs().sum(axis=1)
    scale = np.where(gross > LEVERAGE_CAP, LEVERAGE_CAP / gross, 1.0)
    monthly_w = monthly_w.mul(scale, axis=0)
    print(f"      Avg active assets : {(monthly_w > 0).sum(axis=1).mean():.1f}/14, max gross : {gross.max():.3f}",
          flush=True)

    print("[4/5] PnL with cash earning rfr...", flush=True)
    active_pnl = (monthly_w.shift(1) * log_ret).sum(axis=1)
    cash_w = (1 - monthly_w.shift(1).abs().sum(axis=1)).clip(lower=0)
    cash_pnl = cash_w * rfr
    turnover = (monthly_w - monthly_w.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS_ETF / 10_000.0
    daily_pnl = active_pnl + cash_pnl - cost

    perf_start = max(LOOKBACKS) + VOL_WINDOW
    perf = daily_pnl.iloc[perf_start:]

    print("[5/5] Metrics...", flush=True)
    sharpe = (perf.mean() / perf.std()) * np.sqrt(TRADING_DAYS)
    eq = (1 + perf).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / len(perf)) - 1
    rmax = eq.cummax()
    dd = (eq - rmax) / rmax
    max_dd = dd.min()
    rolling_sharpe = perf.rolling(252).mean() / perf.rolling(252).std() * np.sqrt(TRADING_DAYS)
    rs_min = rolling_sharpe.dropna().min()
    rs_max = rolling_sharpe.dropna().max()
    rs_median = rolling_sharpe.dropna().median()
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf.index < mid]
    h2 = perf[perf.index >= mid]
    sh_h1 = (h1.mean() / h1.std()) * np.sqrt(TRADING_DAYS) if h1.std() != 0 else 0
    sh_h2 = (h2.mean() / h2.std()) * np.sqrt(TRADING_DAYS) if h2.std() != 0 else 0
    delta_sub = abs(sh_h1 - sh_h2)

    # SPY beta
    spy_path = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
    df_spy = pd.read_parquet(spy_path)[["date", "Adj Close"]]
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["Adj Close"].pct_change()
    pair = pd.DataFrame({"date": perf.index.values, "ret": perf.values})
    merged = pair.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    beta_spy = float(cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0)

    print(f"      Sharpe = {sharpe:.3f}, CAGR = {cagr*100:.2f}%, MaxDD = {max_dd*100:.2f}%", flush=True)
    print(f"      Calmar = {cagr/abs(max_dd) if max_dd != 0 else 0:.2f}, β SPY = {beta_spy:+.4f}", flush=True)
    print(f"      Rolling 252d Sharpe : min {rs_min:.2f}, median {rs_median:.2f}, max {rs_max:.2f}", flush=True)
    print(f"      Hard split h1/h2 : {sh_h1:.3f}/{sh_h2:.3f}, Δ={delta_sub:.3f}", flush=True)

    # Decision
    if sharpe > 1.5 and abs(max_dd) < 0.20 and delta_sub < 0.5:
        decision = "Stage 1 PASS — Universe extended TSMOM débloque significant edge"
        emoji = "✅ STAGE 1 PASS"
    elif sharpe > 1.0 and abs(max_dd) < 0.25:
        decision = f"Marginal-good (Sharpe {sharpe:.3f}, DD {max_dd*100:.1f}%) — sub-sample stability {delta_sub:.2f}"
        emoji = "⚠️ MARGINAL"
    elif sharpe < 0.7:
        decision = f"ARCHIVE — Sharpe {sharpe:.3f} < 0.7, universe expansion ne suffit pas"
        emoji = "🛑 ARCHIVE"
    else:
        decision = f"Marginal (Sharpe {sharpe:.3f}, DD {max_dd*100:.1f}%) — useful for ensemble"
        emoji = "⚠️ MARGINAL"

    md_lines = []
    md_lines.append("# Cycle 12 — TSMOM 14-asset extended universe + corrections")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Universe (14 assets, 6 categories)")
    md_lines.append("")
    by_cat = {}
    for sym, cat in ASSETS.items():
        by_cat.setdefault(cat, []).append(sym)
    for cat, syms in by_cat.items():
        md_lines.append(f"- **{cat}** : {', '.join(syms)}")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net | **{sharpe:.3f}** |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {max_dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {cagr/abs(max_dd) if max_dd != 0 else 0:.2f} |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} |")
    md_lines.append(f"| Rolling 252d Sharpe | min {rs_min:.2f} / median {rs_median:.2f} / max {rs_max:.2f} |")
    md_lines.append(f"| Sub-sample h1/h2 (split 2022-09) | {sh_h1:.3f}/{sh_h2:.3f} (Δ={delta_sub:.3f}) |")
    md_lines.append("")
    md_lines.append("## Comparaison vs cycles précédents")
    md_lines.append("")
    md_lines.append("| Cycle | Universe | Sharpe |")
    md_lines.append("|---|---|---:|")
    md_lines.append(f"| Cycle 2 baseline TSMOM 4etf | SPY/QQQ/GLD/TLT | 0.96 |")
    md_lines.append(f"| Cycle 10 recomputed TSMOM 4etf | SPY/QQQ/GLD/TLT | 0.79 |")
    md_lines.append(f"| Cycle 11 corrected 4etf | SPY/QQQ/GLD/TLT | 0.94 |")
    md_lines.append(f"| **Cycle 12 corrected 14 asset universe** | 6 categories | **{sharpe:.3f}** |")
    md_lines.append("")
    out_md = OUT_DIR / "cycle12_tsmom_extended_universe_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_frame("pnl").to_parquet(OUT_DIR / "cycle12_tsmom_extended_pnl.parquet")
    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Sharpe : {sharpe:.3f} | {emoji} | {decision}", flush=True)


if __name__ == "__main__":
    main()
