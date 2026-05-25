"""run_cycle7_avellaneda_weekly.py — R&D Cycle v4 / Cycle 7 Avellaneda-Lee PCA WEEKLY horizon.

Hypothèse pré-spec :
  Cycle v3 insight structural : daily SP500 retail liquide → residuals/spreads = essentially
  random walks (half-life 0.6-0.7d, mean-reversion price out par institutional arbitrage).
  HYPOTHESE : à horizon hebdomadaire, microstructure noise s'agrège → smoother → slower
  mean-reversion (Lo-MacKinlay 1990) peut être détectable + tradable.
  Same Avellaneda-Lee méthodologie que Cycle 5 mais resampled weekly returns.
  Forme falsifiable : Sharpe net > 0.6 + |β SPY|<0.1 + half-life 1-8 weeks (5-40d) + ΔSub<0.4.

Anti-lookahead :
  - Resample weekly Friday-close (last trading day per week)
  - Rolling 52-week PCA past-only
  - Z-score 12-week past-only (3 months)
  - Signal at week t-1 close → trade week t close

Univers : SP500 503 tickers (483 full coverage 6.5y).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

PCA_WINDOW_W = 52  # 52 weeks (1y)
ZSCORE_WINDOW_W = 12  # 12 weeks (3 months)
ENTRY_Z = 1.5
DECILE_FRACTION = 0.10
RT_BPS_PER_LEG = 10
WEEKS_PER_YEAR = 52
N_PC = 1


def load_weekly_returns() -> pd.DataFrame:
    df = pd.read_parquet(SP500_PRICES_PATH)
    df = df[["symbol", "date", "adj_close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    # Resample weekly Friday-close
    weekly = pivot.resample("W-FRI").last()
    coverage = (~weekly.isna()).mean()
    keep = coverage[coverage >= 0.90].index.tolist()
    weekly = weekly[keep]
    log_ret = np.log(weekly).diff()
    return log_ret


def compute_residuals_and_z_weekly(log_ret: pd.DataFrame, n_pc: int = N_PC,
                                     pca_window: int = PCA_WINDOW_W,
                                     zscore_window: int = ZSCORE_WINDOW_W
                                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(log_ret)
    cols = log_ret.columns.tolist()
    residuals = pd.DataFrame(index=log_ret.index, columns=cols, dtype=float)
    for i in range(pca_window, n):
        past = log_ret.iloc[i - pca_window:i].dropna(axis=1, how="any")
        if past.shape[1] < 50:
            continue
        try:
            pca = PCA(n_components=n_pc)
            pca.fit(past.values)
        except Exception:
            continue
        pc1_loading = pca.components_[0]
        current = log_ret.iloc[i][past.columns].values
        if np.isnan(current).any():
            continue
        pc1_ret_t = float(np.dot(current, pc1_loading))
        pc1_past = past.values @ pc1_loading
        var_pc1 = np.var(pc1_past)
        if var_pc1 == 0:
            continue
        for j, sym in enumerate(past.columns):
            cov = np.cov(past[sym].values, pc1_past)[0, 1]
            beta = cov / var_pc1
            residuals.at[log_ret.index[i], sym] = current[j] - beta * pc1_ret_t
    z = residuals.copy()
    for sym in cols:
        s = residuals[sym]
        mean = s.rolling(zscore_window, min_periods=zscore_window).mean().shift(1)
        std = s.rolling(zscore_window, min_periods=zscore_window).std().shift(1)
        z[sym] = (s - mean) / std
    return residuals, z


def simulate_weekly_long_short_decile(log_ret: pd.DataFrame, z: pd.DataFrame,
                                         entry_z: float, decile_frac: float,
                                         bps_per_leg: float) -> pd.DataFrame:
    n = len(log_ret)
    weekly_pnl = pd.Series(0.0, index=log_ret.index)
    n_longs = pd.Series(0, index=log_ret.index)
    n_shorts = pd.Series(0, index=log_ret.index)
    prev_long: set[str] = set()
    prev_short: set[str] = set()
    for i in range(2, n):
        z_y = z.iloc[i - 1].dropna()
        if len(z_y) < 20:
            continue
        n_decile = max(1, int(len(z_y) * decile_frac))
        sorted_z = z_y.sort_values()
        long_set = set(sorted_z.head(n_decile).index)
        short_set = set(sorted_z.tail(n_decile).index)
        long_set = {s for s in long_set if z_y[s] < -entry_z}
        short_set = {s for s in short_set if z_y[s] > entry_z}
        if not long_set and not short_set:
            continue
        today_ret = log_ret.iloc[i]
        long_ret = today_ret[list(long_set)].mean() if long_set else 0.0
        short_ret = today_ret[list(short_set)].mean() if short_set else 0.0
        spread_ret = (long_ret if long_set else 0.0) - (short_ret if short_set else 0.0)
        new_l = long_set - prev_long
        new_s = short_set - prev_short
        cost = ((len(new_l) / max(1, len(long_set))) + (len(new_s) / max(1, len(short_set)))) * bps_per_leg / 10_000.0
        weekly_pnl.iloc[i] = spread_ret - cost
        n_longs.iloc[i] = len(long_set)
        n_shorts.iloc[i] = len(short_set)
        prev_long = long_set
        prev_short = short_set
    return pd.DataFrame({
        "date": log_ret.index,
        "pnl": weekly_pnl.values,
        "n_longs": n_longs.values,
        "n_shorts": n_shorts.values,
    })


def compute_sharpe_weekly(returns: np.ndarray) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(WEEKS_PER_YEAR))


def compute_dd_calmar_weekly(returns: np.ndarray) -> tuple[float, float, float]:
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    eq = np.cumprod(1 + r)
    cagr = eq[-1] ** (WEEKS_PER_YEAR / len(r)) - 1
    rmax = np.maximum.accumulate(eq)
    dd = (eq - rmax) / rmax
    return float(cagr), float(dd.min()), float(cagr / abs(dd.min()) if dd.min() < 0 else 0.0)


def beta_vs_spy_weekly(returns: np.ndarray, dates: pd.Series) -> float:
    df_spy = pd.read_parquet(SPY_PATH)[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy = df_spy.set_index("date").resample("W-FRI").last().reset_index()
    df_spy["spy_ret"] = df_spy["spy_adj"].pct_change()
    pair = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
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
    print("[Cycle 7] Avellaneda-Lee PCA stat-arb WEEKLY horizon", flush=True)
    print(f"  Resample weekly Friday-close, PCA rolling {PCA_WINDOW_W}w, z-score {ZSCORE_WINDOW_W}w", flush=True)
    print(f"  Entry |z|>{ENTRY_Z}, decile {DECILE_FRACTION:.0%}, costs {RT_BPS_PER_LEG} bps/leg", flush=True)
    print("  Hypothesis : daily noise → weekly aggregate → slower mean-reversion exploitable", flush=True)

    # 1) Load weekly returns
    print("[1/4] Loading SP500 weekly returns matrix...", flush=True)
    log_ret = load_weekly_returns()
    print(f"      Shape : {log_ret.shape}, period {log_ret.index.min().date()} → {log_ret.index.max().date()}",
          flush=True)

    # 2) PCA + residuals + z-score
    print(f"[2/4] Rolling PCA + residuals + z-score (weekly past-only)...", flush=True)
    residuals, z = compute_residuals_and_z_weekly(log_ret)
    print(f"      Residuals computed for {residuals.notna().sum().sum()} (sym×wk) cells", flush=True)

    # 3) Simulate
    print("[3/4] Simulating weekly long-short decile...", flush=True)
    sim = simulate_weekly_long_short_decile(log_ret, z,
                                              entry_z=ENTRY_Z,
                                              decile_frac=DECILE_FRACTION,
                                              bps_per_leg=RT_BPS_PER_LEG)
    n_active = (sim["n_longs"] + sim["n_shorts"] > 0).sum()
    print(f"      Active weeks : {n_active}/{len(sim)}", flush=True)

    # Skip warmup
    perf = sim.iloc[PCA_WINDOW_W + ZSCORE_WINDOW_W:].reset_index(drop=True)

    # 4) Metrics + decision
    print("[4/4] Metrics + decision...", flush=True)
    sharpe = compute_sharpe_weekly(perf["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar_weekly(perf["pnl"].values)
    beta_spy = beta_vs_spy_weekly(perf["pnl"].values, perf["date"])
    half_lives = []
    for sym in residuals.columns[:50]:
        hl = half_life_ou(residuals[sym])
        if not np.isnan(hl):
            half_lives.append(hl)
    avg_hl = float(np.median(half_lives)) if half_lives else float("nan")
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid]
    h2 = perf[perf["date"] >= mid]
    sh_h1 = compute_sharpe_weekly(h1["pnl"].values)
    sh_h2 = compute_sharpe_weekly(h2["pnl"].values)
    delta_sub = abs(sh_h1 - sh_h2)
    print(f"      Sharpe = {sharpe:.3f} (annualized weekly), CAGR = {cagr*100:.2f}%, "
          f"MaxDD = {dd*100:.2f}%, |β SPY|={abs(beta_spy):.4f}", flush=True)
    print(f"      half-life median = {avg_hl:.1f} weeks ({avg_hl*5:.1f} trading days), Δsub = {delta_sub:.2f}", flush=True)

    # Decision
    archive = []
    if sharpe < 0.5:
        archive.append(f"Sharpe {sharpe:.3f} < 0.5")
    if abs(beta_spy) > 0.2:
        archive.append(f"|β SPY| {abs(beta_spy):.3f} > 0.2")
    if delta_sub > 0.5:
        archive.append(f"ΔSharpe sub {delta_sub:.2f} > 0.5")
    if not (1 <= avg_hl <= 8):  # 1-8 weeks = 5-40 trading days
        if not np.isnan(avg_hl):
            archive.append(f"half-life {avg_hl:.1f}w outside [1, 8w]")
    if archive:
        decision = "ARCHIVE — " + " ; ".join(archive)
        emoji = "🛑 ARCHIVE"
    elif sharpe > 0.7 and abs(beta_spy) < 0.1 and delta_sub < 0.4 and 1 <= avg_hl <= 8:
        decision = "Stage 1 PASS — Avellaneda-Lee weekly horizon débloque mean-reversion"
        emoji = "✅ STAGE 1 PASS"
    else:
        decision = (f"Marginal (Sharpe {sharpe:.3f}, |β|={abs(beta_spy):.3f}, hl={avg_hl:.1f}w, "
                    f"Δsub={delta_sub:.2f}) — ARCHIVE strict per discipline")
        emoji = "🛑 ARCHIVE (marginal)"

    md_lines = []
    md_lines.append("# Cycle 7 — Avellaneda-Lee PCA stat-arb WEEKLY horizon")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v4 — Cycle 7 (post-Cycle v3 insight half-life 0.7d daily saturated)")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : Cycle v3 a observé half-life 0.6-0.7d cross 4 implémentations daily SP500 "
                     f"= mean-reversion price out daily par institutional arb. Lo-MacKinlay 1990 montre "
                     f"mean-reversion fundamentals opère sur semaines-mois. Resample weekly + Avellaneda-Lee "
                     f"PCA même méthodologie = test si half-life shifts à 1-8 weeks (5-40 days).")
    md_lines.append(f"- **Univers** : SP500 503 tickers, weekly Friday-close 2019-06 → 2025-11 (~338 weeks)")
    md_lines.append(f"- **Méthodologie** : Resample weekly + rolling 52w PCA past-only + z-score 12w past-only + "
                     f"long bottom-decile / short top-decile équipondéré dollar-neutral")
    md_lines.append("")
    md_lines.append("## Métriques (annualized via √52)")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net | {sharpe:.3f} |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} |")
    md_lines.append(f"| Half-life OU (median 50 stocks) | {avg_hl:.1f} weeks ({avg_hl*5:.1f} days) |")
    md_lines.append(f"| Sub-sample h1/h2 | h1={sh_h1:.2f}, h2={sh_h2:.2f}, Δ={delta_sub:.2f} |")
    md_lines.append(f"| Active weeks | {n_active}/{len(sim)} |")
    md_lines.append("")
    md_lines.append("## Comparaison vs Cycle 5 (daily)")
    md_lines.append("")
    md_lines.append(f"| Métrique | Daily (Cycle 5) | Weekly (Cycle 7) |")
    md_lines.append(f"|---|---:|---:|")
    md_lines.append(f"| Sharpe net | -1.71 | {sharpe:.3f} |")
    md_lines.append(f"| Half-life | 0.7d | {avg_hl:.1f}w ({avg_hl*5:.1f}d) |")
    md_lines.append(f"| Verdict | ARCHIVE | {emoji} |")
    md_lines.append("")
    out_md = OUT_DIR / "cycle7_avellaneda_weekly_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_parquet(OUT_DIR / "cycle7_avellaneda_weekly_pnl.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
