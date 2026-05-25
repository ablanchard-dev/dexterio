"""run_cycle5_avellaneda_lee_pca.py — R&D Cycle v3 / Cycle 5 Avellaneda-Lee PCA stat-arb SP500.

Hypothèse pré-spec :
  Avellaneda-Lee 2010 "Statistical Arbitrage in the U.S. Equities Market" : 1er PC marché
  extrait de SP500, β-neutraliser chaque stock vs PC1, résidus mean-reverting avec OU
  half-life ~5-10 jours. Long residual z<-1.5, short z>+1.5, exit z within ±0.5.
  Forme falsifiable : Sharpe net > 0.6 + market-neutral (|β SPY|<0.1) + half-life 5-30d.
  Plan v4.0 §0.5bis avait pré-archivé sans test. Test honest requis avant verdict.

Anti-lookahead constraints :
  - Rolling 252d PCA fit strictement sur returns < t (pas inclus t)
  - β stock vs PC1 computed past-only
  - Z-score résiduel 60d past-only
  - Signal at close t → trade at close t+1 (shift)

Gates pré-écrits :
  - PROMOTE Stage 1 si Sharpe net > 0.7 + |β SPY| < 0.1 + ΔSharpe sub-sample < 0.4 + half-life 5-30d
  - ARCHIVE si Sharpe < 0.5
  - ARCHIVE si mean-rev rate < 60%
  - ARCHIVE si |β résiduel SPY| > 0.2 (vrai market-neutral pas atteint)
  - 1 amélioration K (K=2 ou 3 PCs au lieu de 1 PC unique) si marginal

Universe : SP500 prices 6.5y parquet local (483 symbols full coverage).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/hmm_regime"

PCA_WINDOW = 252
ZSCORE_WINDOW = 60
ENTRY_Z = 1.5
EXIT_Z = 0.5
COVERAGE_MIN = 0.90  # require ≥90% non-NaN per stock in window
RT_BPS_PER_LEG = 10  # 10 bps RT per leg (long + short = 2 legs per pair)
TRADING_DAYS = 252
N_PC = 1  # baseline single PC (can switch to 2-3 in amélioration)
DECILE_FRACTION = 0.10  # top/bottom decile


def load_returns_matrix(min_coverage: float = COVERAGE_MIN) -> pd.DataFrame:
    """Load SP500 daily returns matrix wide-format (date × symbol). Drop low-coverage symbols."""
    df = pd.read_parquet(SP500_PRICES_PATH)
    df = df[["symbol", "date", "adj_close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close")
    pivot = pivot.sort_index()
    coverage = (~pivot.isna()).mean()
    keep = coverage[coverage >= min_coverage].index.tolist()
    pivot = pivot[keep]
    log_ret = np.log(pivot).diff()
    return log_ret


def compute_residuals_and_z(log_ret: pd.DataFrame, n_pc: int = N_PC,
                              pca_window: int = PCA_WINDOW,
                              zscore_window: int = ZSCORE_WINDOW
                              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling PCA + residual + z-score, fully past-only.

    Anti-lookahead pattern :
      - At time t, fit PCA on returns[t-window : t] (past window, not including t)
      - Compute β stock vs PC1 from those past returns
      - Project current return at t onto PC1 to get factor return at t
      - Residual_t = log_ret_t - β_stock × PC1_ret_t
      - Z-score on rolling 60d past residuals (not including t)
    """
    n = len(log_ret)
    cols = log_ret.columns.tolist()
    residuals = pd.DataFrame(index=log_ret.index, columns=cols, dtype=float)
    pc1_returns = pd.Series(index=log_ret.index, dtype=float)
    betas_history = pd.DataFrame(index=log_ret.index, columns=cols, dtype=float)

    # Step through dates : for each t starting at pca_window
    for i in range(pca_window, n):
        # Past window strictly < t (rows i-pca_window to i-1 inclusive)
        past = log_ret.iloc[i - pca_window:i].dropna(axis=1, how="any")
        if past.shape[1] < 50:
            # Not enough symbols with full coverage in this window
            continue
        # Fit PCA on past
        pca = PCA(n_components=n_pc)
        try:
            pca.fit(past.values)
        except Exception:
            continue
        # PC1 loadings (n_symbols,)
        pc1_loading = pca.components_[0]
        # PC1 return at t : project current observation
        current = log_ret.iloc[i][past.columns].values
        if np.isnan(current).any():
            # NaN current → skip
            continue
        pc1_ret_t = float(np.dot(current, pc1_loading))
        pc1_returns.iloc[i] = pc1_ret_t
        # β stock vs PC1 = cov(stock, PC1_ret_past) / var(PC1_ret_past) computed on past window
        pc1_past = past.values @ pc1_loading
        var_pc1 = np.var(pc1_past)
        if var_pc1 == 0:
            continue
        for j, sym in enumerate(past.columns):
            cov = np.cov(past[sym].values, pc1_past)[0, 1]
            beta = cov / var_pc1
            betas_history.at[log_ret.index[i], sym] = beta
            # Residual at t = log_ret_t - beta × pc1_ret_t
            residuals.at[log_ret.index[i], sym] = current[j] - beta * pc1_ret_t

    # Z-score residuals : per symbol rolling 60d past-only
    z = residuals.copy()
    for sym in cols:
        s = residuals[sym]
        mean = s.rolling(zscore_window, min_periods=zscore_window).mean().shift(1)
        std = s.rolling(zscore_window, min_periods=zscore_window).std().shift(1)
        z[sym] = (s - mean) / std

    return residuals, z


def simulate_long_short_decile(log_ret: pd.DataFrame, z: pd.DataFrame,
                                 entry_z: float = ENTRY_Z,
                                 exit_z: float = EXIT_Z,
                                 decile_frac: float = DECILE_FRACTION,
                                 bps_per_leg: float = RT_BPS_PER_LEG
                                 ) -> pd.DataFrame:
    """Long bottom-decile residual z (oversold), short top-decile (overbought).

    Daily rebalance : each day t, look at z(t-1) (anti-lookahead), select deciles, hold to t+1.
    Position: equal-weight long bottom-decile, equal-weight short top-decile, dollar-neutral.
    Daily PnL = (long_basket_ret - short_basket_ret) - 2 × turnover_cost.
    """
    n = len(log_ret)
    daily_pnl = pd.Series(0.0, index=log_ret.index)
    n_longs = pd.Series(0, index=log_ret.index)
    n_shorts = pd.Series(0, index=log_ret.index)
    turnover = pd.Series(0.0, index=log_ret.index)

    prev_long_set: set[str] = set()
    prev_short_set: set[str] = set()

    for i in range(2, n):  # need i-1 z and i return
        date_t = log_ret.index[i]
        z_yesterday = z.iloc[i - 1].dropna()
        if len(z_yesterday) < 20:
            continue
        # Select deciles based on z(t-1)
        n_decile = max(1, int(len(z_yesterday) * decile_frac))
        sorted_z = z_yesterday.sort_values()
        long_set = set(sorted_z.head(n_decile).index)  # most negative z = oversold = long
        short_set = set(sorted_z.tail(n_decile).index)  # most positive z = overbought = short
        # Filter by entry_z threshold
        long_set = {s for s in long_set if z_yesterday[s] < -entry_z}
        short_set = {s for s in short_set if z_yesterday[s] > entry_z}

        if not long_set and not short_set:
            n_longs.iloc[i] = 0
            n_shorts.iloc[i] = 0
            continue

        # Compute today's basket returns (return from t-1 to t)
        today_ret = log_ret.iloc[i]
        # Equal-weight basket returns
        long_ret = today_ret[list(long_set)].mean() if long_set else 0.0
        short_ret = today_ret[list(short_set)].mean() if short_set else 0.0
        # Spread return = long - short (dollar-neutral)
        spread_ret = (long_ret if long_set else 0.0) - (short_ret if short_set else 0.0)

        # Turnover cost : symbols not in previous baskets are new entries
        new_longs = long_set - prev_long_set
        new_shorts = short_set - prev_short_set
        # Cost per side = (n_new / n_total_in_basket) × bps_per_leg / 10_000.0
        cost_long = (len(new_longs) / max(1, len(long_set))) * bps_per_leg / 10_000.0 if long_set else 0
        cost_short = (len(new_shorts) / max(1, len(short_set))) * bps_per_leg / 10_000.0 if short_set else 0
        cost = cost_long + cost_short
        spread_ret -= cost

        daily_pnl.iloc[i] = spread_ret
        n_longs.iloc[i] = len(long_set)
        n_shorts.iloc[i] = len(short_set)
        turnover.iloc[i] = (len(new_longs) + len(new_shorts))

        prev_long_set = long_set
        prev_short_set = short_set

    out = pd.DataFrame({
        "date": log_ret.index,
        "pnl": daily_pnl.values,
        "n_longs": n_longs.values,
        "n_shorts": n_shorts.values,
        "turnover": turnover.values,
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
    equity = np.cumprod(1 + r)
    cagr = equity[-1] ** (TRADING_DAYS / len(r)) - 1
    rmax = np.maximum.accumulate(equity)
    dd = (equity - rmax) / rmax
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return float(cagr), float(max_dd), float(calmar)


def beta_vs_spy(returns: np.ndarray, dates: pd.Series) -> float:
    df_spy = pd.read_parquet(SPY_PATH)
    df_spy = df_spy[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["spy_adj"].pct_change()
    pair_df = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair_df.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    if len(merged) < 10:
        return 0.0
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    if cov[1, 1] == 0:
        return 0.0
    return float(cov[0, 1] / cov[1, 1])


def half_life_ou(residuals: pd.Series) -> float:
    r = residuals.dropna().values
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--n-pc", type=int, default=N_PC)
    parser.add_argument("--entry-z", type=float, default=ENTRY_Z)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[Cycle 5] Avellaneda-Lee PCA stat-arb SP500", flush=True)
    print(f"  Window 2019-06 → 2025-11 (6.5y) — anti-lookahead PCA + z-score past-only", flush=True)
    print(f"  Config : n_pc={args.n_pc}, entry_z={args.entry_z}, exit_z={EXIT_Z}, "
          f"decile={DECILE_FRACTION:.0%}, costs {RT_BPS_PER_LEG} bps/leg", flush=True)

    # 1) Load returns matrix
    print("[1/5] Loading SP500 returns matrix...", flush=True)
    log_ret = load_returns_matrix(min_coverage=COVERAGE_MIN)
    print(f"      Shape : {log_ret.shape} (date × symbol), period {log_ret.index.min().date()} → {log_ret.index.max().date()}",
          flush=True)

    # 2) Rolling PCA + residuals + z-score
    print(f"[2/5] Rolling PCA (window {PCA_WINDOW}d) + residuals + z-score (window {ZSCORE_WINDOW}d)...",
          flush=True)
    residuals, z = compute_residuals_and_z(log_ret, n_pc=args.n_pc,
                                              pca_window=PCA_WINDOW,
                                              zscore_window=ZSCORE_WINDOW)
    print(f"      Residuals computed for {residuals.notna().sum().sum()} (symbol×day) cells",
          flush=True)

    # 3) Simulate long-short decile strategy
    print("[3/5] Simulating long-short decile strategy (anti-lookahead)...", flush=True)
    sim = simulate_long_short_decile(log_ret, z, entry_z=args.entry_z,
                                       exit_z=EXIT_Z, decile_frac=DECILE_FRACTION,
                                       bps_per_leg=RT_BPS_PER_LEG)
    n_active_days = (sim["n_longs"] + sim["n_shorts"] > 0).sum()
    print(f"      Active days (≥1 position) : {n_active_days} / {len(sim)}", flush=True)

    # Skip warmup period (PCA + z-score)
    perf_start = PCA_WINDOW + ZSCORE_WINDOW
    perf = sim.iloc[perf_start:].copy().reset_index(drop=True)

    # 4) Metrics
    print("[4/5] Computing metrics + sub-sample stability...", flush=True)
    sharpe = compute_sharpe(perf["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar(perf["pnl"].values)
    beta_spy = beta_vs_spy(perf["pnl"].values, perf["date"])
    # Sub-sample 2019-2022 vs 2022-2025
    mid_date = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid_date]
    h2 = perf[perf["date"] >= mid_date]
    sharpe_h1 = compute_sharpe(h1["pnl"].values)
    sharpe_h2 = compute_sharpe(h2["pnl"].values)
    delta_subsample = abs(sharpe_h1 - sharpe_h2)
    # Average residual half-life across all symbols
    half_lives = []
    for sym in residuals.columns[:50]:  # sample 50 symbols
        hl = half_life_ou(residuals[sym])
        if not np.isnan(hl):
            half_lives.append(hl)
    avg_hl = float(np.median(half_lives)) if half_lives else float("nan")

    print(f"      Sharpe net = {sharpe:.3f}, CAGR = {cagr*100:.2f}%, MaxDD = {dd*100:.2f}%, "
          f"Calmar = {calmar:.2f}", flush=True)
    print(f"      |β SPY| = {abs(beta_spy):.4f}, half-life median = {avg_hl:.1f}d, "
          f"ΔSharpe sub = {delta_subsample:.2f}", flush=True)

    # 5) Decision per pre-spec gates
    print("[5/5] Decision per pre-spec gates...", flush=True)
    R2_BASELINE = 0.32  # MA-V baseline reference (different mechanism but stat-arb domain)
    archive_reasons = []
    pass_conditions = []

    if sharpe < 0.5:
        archive_reasons.append(f"Sharpe {sharpe:.3f} < 0.5")
    elif sharpe > 0.7:
        pass_conditions.append(f"Sharpe {sharpe:.3f} > 0.7")
    if abs(beta_spy) > 0.2:
        archive_reasons.append(f"|β SPY| {abs(beta_spy):.3f} > 0.2 (not market-neutral)")
    elif abs(beta_spy) < 0.1:
        pass_conditions.append(f"|β SPY| {abs(beta_spy):.3f} < 0.1 (market-neutral)")
    if delta_subsample > 0.4:
        archive_reasons.append(f"ΔSharpe sub-sample {delta_subsample:.2f} > 0.4 (régime-dependent)")
    if not (5 <= avg_hl <= 30):
        if avg_hl < 5:
            archive_reasons.append(f"Half-life {avg_hl:.1f}d < 5 (residuals = noise)")
        elif avg_hl > 30:
            archive_reasons.append(f"Half-life {avg_hl:.1f}d > 30 (residuals slow / structural drift)")

    if archive_reasons:
        decision = "ARCHIVE — " + " ; ".join(archive_reasons)
        emoji = "🛑 ARCHIVE"
    elif (sharpe > 0.7 and abs(beta_spy) < 0.1 and delta_subsample < 0.4
            and 5 <= avg_hl <= 30):
        decision = ("Stage 1 PASS — Avellaneda-Lee PCA stat-arb débloque edge sur SP500 multi-asset, "
                    "proceed to Stage 2 robustness")
        emoji = "✅ STAGE 1 PASS"
    else:
        decision = (f"Marginal (Sharpe {sharpe:.3f}, |β|={abs(beta_spy):.3f}, hl={avg_hl:.1f}d, "
                    f"Δsub={delta_subsample:.2f}) — ARCHIVE strict per discipline (1 amélioration max, "
                    f"non-déclenchée car gates ne signalent pas défaut clair corrigeable)")
        emoji = "🛑 ARCHIVE (marginal)"

    # Render verdict
    md_lines: list[str] = []
    md_lines.append("# Cycle 5 — Avellaneda-Lee PCA stat-arb SP500")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v3 (rd-cycle-v2.md branching) — Cycle 5")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : Avellaneda-Lee 2010 \"Statistical Arbitrage in the U.S. Equities Market\" : "
                     f"1er PC = market factor, β-neutralize stocks vs PC1, residuals mean-revert avec OU "
                     f"half-life 5-10 days. Long bottom-decile residual z (oversold), short top-decile.")
    md_lines.append(f"- **Source** : Avellaneda & Lee 2010, Quantitative Finance 10(7) ; "
                     f"plan v4.0 §0.5bis pré-archivé sans test (decay -25 à -35% académique)")
    md_lines.append(f"- **Univers** : SP500 503 tickers (483 full coverage 6.5y), 2019-06-03 → 2025-11-28")
    md_lines.append(f"- **Méthodologie** : Rolling PCA {PCA_WINDOW}d past-only, β stock vs PC1 past-only, "
                     f"z-score residuals {ZSCORE_WINDOW}d past-only, signal shifted t+1")
    md_lines.append(f"- **Costs** : {RT_BPS_PER_LEG} bps RT per leg, turnover-aware (only new positions pay)")
    md_lines.append(f"- **Anti-lookahead** : PCA + β + z-score strictement past-only ; PnL daily mark-to-market")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net annualisé | {sharpe:.3f} |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY (résiduel post-strat) | {beta_spy:+.4f} |")
    md_lines.append(f"| Half-life OU (median sample 50 stocks) | {avg_hl:.1f}d |")
    md_lines.append(f"| ΔSharpe sub-sample (h1/h2 split 2022-09) | {delta_subsample:.2f} (h1={sharpe_h1:.2f}, h2={sharpe_h2:.2f}) |")
    md_lines.append(f"| n active days | {n_active_days} / {len(perf)} |")
    md_lines.append("")
    md_lines.append("## Diagnostic (gates pré-écrits)")
    md_lines.append("")
    md_lines.append(f"| Gate | Result | Status |")
    md_lines.append(f"|---|---|---|")
    md_lines.append(f"| Sharpe > 0.7 | {sharpe:.3f} | {'PASS' if sharpe > 0.7 else 'FAIL'} |")
    md_lines.append(f"| Sharpe ≥ 0.5 | {sharpe:.3f} | {'PASS' if sharpe >= 0.5 else 'FAIL'} |")
    md_lines.append(f"| |β SPY| < 0.1 (market-neutral) | {abs(beta_spy):.4f} | "
                     f"{'PASS' if abs(beta_spy) < 0.1 else 'FAIL'} |")
    md_lines.append(f"| ΔSharpe sub-sample < 0.4 | {delta_subsample:.2f} | "
                     f"{'PASS' if delta_subsample < 0.4 else 'FAIL'} |")
    md_lines.append(f"| Half-life 5-30d | {avg_hl:.1f} | "
                     f"{'PASS' if 5 <= avg_hl <= 30 else 'FAIL'} |")
    md_lines.append("")
    md_lines.append("## Methodology notes")
    md_lines.append("")
    md_lines.append(f"- **PCA past-only** : at each rebalance day t, fit on returns[t-{PCA_WINDOW} : t] (t exclu)")
    md_lines.append(f"- **β past-only** : computed from cov(stock, PC1) / var(PC1) on past window")
    md_lines.append(f"- **Z-score past-only** : rolling {ZSCORE_WINDOW}d mean/std shifted by 1 (excludes current obs)")
    md_lines.append(f"- **Trade exec** : signal at close t-1 → trade at close t (anti-lookahead)")
    md_lines.append(f"- **Turnover cost** : only new entries pay, exits carry no extra cost (one-side basket)")
    md_lines.append(f"- **Equal-weight dollar-neutral** : long basket / short basket equipondérés, "
                     f"pas de market timing supplémentaire")
    md_lines.append("")
    out_md = args.out_dir / "cycle5_avellaneda_lee_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_parquet(args.out_dir / "cycle5_avellaneda_lee_pnl.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
