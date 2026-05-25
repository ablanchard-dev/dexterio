"""run_cycle8_johansen_cross_asset.py — R&D Cycle v4 / Cycle 8 Johansen cross-asset trio.

Hypothèse pré-spec :
  Cycle v3+v4 ont confirmé saturation stat-arb intra-equity (daily + weekly half-life 0.7 noise).
  HYPOTHESE : cross-asset trio (TLT bonds + SPY equity + GLD gold) = 3 asset classes différentes,
  possible équilibre macro long-terme via économie réelle (real rates / inflation / risk-on/off).
  Johansen sur trio = test si cointégration multi-asset class révèle mean-reversion exploitable.
  Forme falsifiable : Sharpe net > 0.6 + |β SPY|<0.3 (acceptable since SPY is component) +
  half-life 5-40d + ΔSub<0.4.

Anti-lookahead :
  - Johansen rolling 252d past-only sur log_prices
  - Eigenvector first (largest eigenvalue) → spread
  - Z-score spread 60d past-only
  - Signal at z[t-1] → trade close t

Univers : f2_daily ETFs SPY + TLT + GLD (3 cross-asset majors, free yfinance).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
F2_DAILY = REPO_ROOT / "backend/data/f2_daily"
SPY_PATH = F2_DAILY / "SPY_1d.parquet"
TLT_PATH = F2_DAILY / "TLT_1d.parquet"
GLD_PATH = F2_DAILY / "GLD_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

JOHANSEN_WINDOW = 252
ZSCORE_WINDOW = 60
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 3.5
RT_BPS_PER_LEG = 5  # ETF spreads tighter than stocks
TRADING_DAYS = 252


def load_etf_prices() -> pd.DataFrame:
    dfs = []
    for path, name in [(SPY_PATH, "SPY"), (TLT_PATH, "TLT"), (GLD_PATH, "GLD")]:
        df = pd.read_parquet(path)[["date", "Adj Close"]].rename(columns={"Adj Close": name})
        df["date"] = pd.to_datetime(df["date"])
        dfs.append(df.set_index("date"))
    out = pd.concat(dfs, axis=1).dropna()
    return out


def rolling_johansen_spread(log_prices: pd.DataFrame, window: int = JOHANSEN_WINDOW
                              ) -> tuple[pd.Series, pd.DataFrame]:
    n = len(log_prices)
    spread = pd.Series(index=log_prices.index, dtype=float)
    eigvecs = pd.DataFrame(index=log_prices.index, columns=log_prices.columns, dtype=float)
    for i in range(window, n):
        past = log_prices.iloc[i - window:i].values
        try:
            result = coint_johansen(past, det_order=0, k_ar_diff=1)
            ev = result.evec[:, 0]
            if ev[0] != 0:
                ev = ev / ev[0]
            spread.iloc[i] = float(np.dot(log_prices.iloc[i].values, ev))
            for j, sym in enumerate(log_prices.columns):
                eigvecs.iloc[i, j] = ev[j]
        except Exception:
            continue
    return spread, eigvecs


def compute_zscore_past(spread: pd.Series, window: int = ZSCORE_WINDOW) -> pd.Series:
    mean = spread.rolling(window, min_periods=window).mean().shift(1)
    std = spread.rolling(window, min_periods=window).std().shift(1)
    return (spread - mean) / std


def simulate_trio_pair_trades(prices: pd.DataFrame, spread: pd.Series,
                                z: pd.Series, eigvecs: pd.DataFrame,
                                entry: float, exit_: float, stop: float,
                                bps_per_leg: float) -> pd.DataFrame:
    n = len(prices)
    daily_pnl = np.zeros(n)
    side = np.zeros(n, dtype=int)
    position = 0
    weights_entry = np.zeros(prices.shape[1])
    for i in range(1, n):
        z_y = z.iloc[i - 1]
        if position != 0:
            today_ret = prices.iloc[i] / prices.iloc[i - 1] - 1
            day_pnl = position * float(np.sum(weights_entry * today_ret.values))
            daily_pnl[i] = day_pnl
            side[i] = position
        if position == 0:
            if not np.isnan(z_y):
                if z_y > entry:
                    position = -1
                    weights_entry = eigvecs.iloc[i - 1].values
                    daily_pnl[i] -= bps_per_leg * len(prices.columns) / 10_000.0
                elif z_y < -entry:
                    position = +1
                    weights_entry = eigvecs.iloc[i - 1].values
                    daily_pnl[i] -= bps_per_leg * len(prices.columns) / 10_000.0
        else:
            should_exit = False
            if not np.isnan(z_y):
                if abs(z_y) < exit_:
                    should_exit = True
                elif abs(z_y) > stop:
                    should_exit = True
            if should_exit:
                daily_pnl[i] -= bps_per_leg * len(prices.columns) / 10_000.0
                position = 0
                weights_entry = np.zeros(prices.shape[1])
    out = pd.DataFrame({
        "date": prices.index,
        "spread": spread.values,
        "z": z.values,
        "pnl": daily_pnl,
        "side": side,
    })
    return out


def compute_sharpe(returns: np.ndarray) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def compute_dd_calmar(returns: np.ndarray) -> tuple[float, float, float]:
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    eq = np.cumprod(1 + r)
    cagr = eq[-1] ** (TRADING_DAYS / len(r)) - 1
    rmax = np.maximum.accumulate(eq)
    dd = (eq - rmax) / rmax
    return float(cagr), float(dd.min()), float(cagr / abs(dd.min()) if dd.min() < 0 else 0.0)


def beta_vs_spy(returns: np.ndarray, dates: pd.Series, prices: pd.DataFrame) -> float:
    spy_ret = prices["SPY"].pct_change().reset_index().rename(columns={"date": "date"})
    spy_ret.columns = ["date", "spy_ret"]
    pair = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair.merge(spy_ret, on="date", how="inner").dropna()
    if len(merged) < 10:
        return 0.0
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    return float(cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0.0)


def half_life_ou(spread: pd.Series) -> float:
    r = spread.dropna().values
    if len(r) < 30:
        return float("nan")
    dr = np.diff(r)
    r_lag = r[:-1]
    if r_lag.std() == 0:
        return float("nan")
    A = np.vstack([r_lag, np.ones(len(r_lag))]).T
    coeffs = np.linalg.lstsq(A, dr, rcond=None)[0]
    theta = float(coeffs[0])
    if theta >= 0:
        return float("nan")
    return float(-np.log(2) / theta)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 8] Johansen cross-asset trio TLT + SPY + GLD", flush=True)
    print(f"  Anti-lookahead : Johansen rolling {JOHANSEN_WINDOW}d past-only, z-score {ZSCORE_WINDOW}d, signal t+1", flush=True)
    print(f"  Costs : {RT_BPS_PER_LEG} bps/leg ETF, entry |z|>{ENTRY_Z}, exit <{EXIT_Z}, stop >{STOP_Z}", flush=True)

    print("[1/4] Loading ETF prices...", flush=True)
    prices = load_etf_prices()
    print(f"      {len(prices)} days, period {prices.index.min().date()} → {prices.index.max().date()}",
          flush=True)
    print(f"      Columns : {prices.columns.tolist()}", flush=True)

    log_prices = np.log(prices)
    print("[2/4] Rolling Johansen + spread + z-score...", flush=True)
    spread, eigvecs = rolling_johansen_spread(log_prices, JOHANSEN_WINDOW)
    z = compute_zscore_past(spread, ZSCORE_WINDOW)

    print("[3/4] Simulating trio pair trades...", flush=True)
    sim = simulate_trio_pair_trades(prices, spread, z, eigvecs,
                                       entry=ENTRY_Z, exit_=EXIT_Z, stop=STOP_Z,
                                       bps_per_leg=RT_BPS_PER_LEG)
    n_trades = int((sim["side"].diff().fillna(0).abs() > 0).sum() // 2)
    print(f"      n_trades : {n_trades}", flush=True)

    perf_start = JOHANSEN_WINDOW + ZSCORE_WINDOW
    perf = sim.iloc[perf_start:].reset_index(drop=True)

    print("[4/4] Metrics + decision...", flush=True)
    sharpe = compute_sharpe(perf["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar(perf["pnl"].values)
    beta_spy = beta_vs_spy(perf["pnl"].values, perf["date"], prices)
    hl = half_life_ou(spread.iloc[perf_start:])
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid]
    h2 = perf[perf["date"] >= mid]
    sh_h1 = compute_sharpe(h1["pnl"].values)
    sh_h2 = compute_sharpe(h2["pnl"].values)
    delta_sub = abs(sh_h1 - sh_h2)
    print(f"      Sharpe = {sharpe:.3f}, CAGR = {cagr*100:.2f}%, MaxDD = {dd*100:.2f}%, "
          f"|β SPY| = {abs(beta_spy):.4f}", flush=True)
    print(f"      half-life = {hl:.1f}d, ΔSub = {delta_sub:.2f}, n_trades = {n_trades}", flush=True)

    archive = []
    if sharpe < 0.5:
        archive.append(f"Sharpe {sharpe:.3f} < 0.5")
    if abs(beta_spy) > 0.3:
        archive.append(f"|β SPY| {abs(beta_spy):.3f} > 0.3 (SPY is component but acceptable up to 0.3)")
    if delta_sub > 0.5:
        archive.append(f"ΔSub {delta_sub:.2f} > 0.5")
    if not (5 <= hl <= 40):
        if not np.isnan(hl):
            archive.append(f"half-life {hl:.1f}d outside [5, 40d]")
    if archive:
        decision = "ARCHIVE — " + " ; ".join(archive)
        emoji = "🛑 ARCHIVE"
    elif sharpe > 0.6 and abs(beta_spy) < 0.3 and delta_sub < 0.4 and 5 <= hl <= 40:
        decision = "Stage 1 PASS — Cross-asset Johansen débloque mean-reversion macro factors"
        emoji = "✅ STAGE 1 PASS"
    else:
        decision = (f"Marginal (Sharpe {sharpe:.3f}, |β|={abs(beta_spy):.3f}, hl={hl:.1f}d) — ARCHIVE strict")
        emoji = "🛑 ARCHIVE (marginal)"

    md_lines = []
    md_lines.append("# Cycle 8 — Johansen cross-asset trio TLT + SPY + GLD")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v4 — Cycle 8 (post-Cycle v3 saturation insight)")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : 3 cross-asset majors (TLT bonds + SPY equity + GLD gold) ont possible "
                     f"équilibre macro long-terme via real rates / inflation / risk-on/off. Johansen test si "
                     f"cointégration cross-class révèle mean-reversion exploitable (où intra-equity stat-arb "
                     f"saturé empiriquement Cycle v3).")
    md_lines.append(f"- **Univers** : SPY + TLT + GLD f2_daily ETFs 6.5y")
    md_lines.append(f"- **Méthodologie** : Johansen rolling {JOHANSEN_WINDOW}d past-only, first eigenvector, "
                     f"z-score {ZSCORE_WINDOW}d past-only, entry |z|>{ENTRY_Z} exit <{EXIT_Z} stop >{STOP_Z}")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net | {sharpe:.3f} |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} |")
    md_lines.append(f"| Half-life OU | {hl:.1f}d |")
    md_lines.append(f"| ΔSub h1/h2 | h1={sh_h1:.2f}, h2={sh_h2:.2f}, Δ={delta_sub:.2f} |")
    md_lines.append(f"| n_trades | {n_trades} |")
    md_lines.append("")
    out_md = OUT_DIR / "cycle8_johansen_cross_asset_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_parquet(OUT_DIR / "cycle8_johansen_cross_asset_pnl.parquet", index=False)
    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
