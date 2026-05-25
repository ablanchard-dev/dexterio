"""run_cycle10_multistrat_ensemble.py — R&D Cycle v5 / Cycle 10 Multi-strategy ensemble portfolio.

Hypothèse pré-spec :
  Sharpe portfolio = avg × √(N / (1 + (N-1)×ρ_avg)) (Bach corpus QUANT 9HD6xo2iO1g).
  Avec edges existants Sharpe 0.7-1.1 individuel et correlation espérée 0.2-0.4 cross-asset,
  ensemble multi-strategy peut atteindre Sharpe portfolio 1.5-2.0+ via diversification.
  Forme falsifiable : Sharpe portfolio (best weighting) > 1.5 + ΔSub-sample < 0.5 + max DD < 25%.

Strategies inputs (existing, recomputed for clean correlation analysis) :
  1. TSMOM 4-asset SPY/QQQ/GLD/TLT (lookback 252d, vol-target equal-weight) — equity + bonds + gold
  2. Crypto TSMOM 5-coin BTC/ETH/BNB/XRP/SOL (lookback 252d) — Cycle 9 baseline
  3. Sector Momentum Top-3 6-month rotation (11 SPDR sectors) — Cycle S+3 T2
  4. SPY buy-hold (passive benchmark, included for correlation reference)
  5. Bond TSMOM TLT alone (single-asset TSMOM)
  6. Gold TSMOM GLD alone

Anti-lookahead :
  - Each strategy computed past-only with proper signal shifting
  - Correlation matrix computed on overlap period only (no peek)
  - Portfolio weights frozen (equal / inverse-vol / risk-parity) — no optimization-driven hindsight

Weighting schemes tested :
  - Equal weight : 1/N
  - Inverse volatility : 1/σ_i normalized
  - Risk parity : weight_i × σ_i × ρ_iP equal across i (iterative)

Gates pré-écrits :
  - Best-weighting Sharpe > 1.5 + DD < 25% + ΔSub < 0.5 → Stage 1 PASS
  - Sharpe < 1.0 → ARCHIVE (no diversification benefit)
  - Marginal → document ceiling, archive
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
F2_DAILY = REPO_ROOT / "backend/data/f2_daily"
SPY_PATH = F2_DAILY / "SPY_1d.parquet"
TLT_PATH = F2_DAILY / "TLT_1d.parquet"
GLD_PATH = F2_DAILY / "GLD_1d.parquet"
QQQ_PATH = F2_DAILY / "QQQ_1d.parquet"
SECTORS_PATH = REPO_ROOT / "backend/data/equities/sectors_11_prices_6.5y.parquet"
CRYPTO_PATH = REPO_ROOT / "backend/data/crypto/crypto_5coins_6.5y.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

LOOKBACK_DAYS = 252
VOL_WINDOW = 60
TRADING_DAYS = 252
TRADING_DAYS_CRYPTO = 365
RT_BPS = 10


def load_etf(path, name):
    df = pd.read_parquet(path)[["date", "Adj Close"]].rename(columns={"Adj Close": name})
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def load_etf_panel():
    spy = load_etf(SPY_PATH, "SPY")
    qqq = load_etf(QQQ_PATH, "QQQ")
    tlt = load_etf(TLT_PATH, "TLT")
    gld = load_etf(GLD_PATH, "GLD")
    return pd.concat([spy, qqq, tlt, gld], axis=1).dropna()


def tsmom_signal(prices: pd.Series, lookback: int, vol_window: int,
                   vol_target: float = 0.15, periods_per_year: int = TRADING_DAYS) -> pd.Series:
    log_ret = np.log(prices).diff()
    r_lookback = (prices.shift(1) / prices.shift(lookback)) - 1
    signal = (r_lookback > 0).astype(int)
    vol = log_ret.shift(1).rolling(vol_window, min_periods=vol_window).std() * np.sqrt(periods_per_year)
    weight = np.where(vol > 0, np.minimum(vol_target / vol, 1.0), 0.0)
    return signal * pd.Series(weight, index=prices.index)


def compute_strat_tsmom_4etf(prices: pd.DataFrame) -> pd.Series:
    """TSMOM equal-weight 4-asset SPY/QQQ/GLD/TLT."""
    log_ret = np.log(prices).diff()
    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    for col in prices.columns:
        weights[col] = tsmom_signal(prices[col], LOOKBACK_DAYS, VOL_WINDOW)
    n_assets = len(prices.columns)
    portfolio_w = weights / n_assets
    daily_pnl = (portfolio_w.shift(1) * log_ret).sum(axis=1)
    turnover = (portfolio_w - portfolio_w.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS / 10_000.0
    return daily_pnl - cost


def compute_strat_single_tsmom(prices: pd.Series) -> pd.Series:
    """TSMOM single-asset."""
    log_ret = np.log(prices).diff()
    weight = tsmom_signal(prices, LOOKBACK_DAYS, VOL_WINDOW)
    daily_pnl = weight.shift(1) * log_ret
    turnover = (weight - weight.shift(1)).abs()
    cost = turnover * RT_BPS / 10_000.0
    return daily_pnl - cost


def compute_strat_crypto_tsmom(crypto_path: Path = CRYPTO_PATH) -> pd.Series:
    """Re-compute crypto TSMOM 5-coin from existing data."""
    df = pd.read_parquet(crypto_path)
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    log_ret = np.log(pivot).diff()
    weights = pd.DataFrame(index=pivot.index, columns=pivot.columns, dtype=float)
    for col in pivot.columns:
        weights[col] = tsmom_signal(pivot[col], LOOKBACK_DAYS, VOL_WINDOW,
                                       vol_target=0.15, periods_per_year=TRADING_DAYS_CRYPTO)
    n_assets = len(pivot.columns)
    portfolio_w = weights / n_assets
    daily_pnl = (portfolio_w.shift(1) * log_ret).sum(axis=1)
    turnover = (portfolio_w - portfolio_w.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS / 10_000.0
    pnl = daily_pnl - cost
    pnl.name = "crypto_tsmom"
    return pnl


def compute_strat_sector_momentum() -> pd.Series:
    """Sector Momentum Top-3 6-month rotation across 11 SPDR sectors."""
    df = pd.read_parquet(SECTORS_PATH)
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    log_ret = np.log(pivot).diff()
    # 6-month return signal (126 trading days)
    lookback = 126
    r_6m = (pivot.shift(1) / pivot.shift(lookback)) - 1
    # Each day: rank, top-3 long
    ranks = r_6m.rank(axis=1, ascending=False)
    top3 = (ranks <= 3).astype(int)
    # Equal-weight 1/3 across top-3
    weights = top3.div(top3.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    # Daily rebalance (could be monthly but daily for simplicity)
    daily_pnl = (weights.shift(1) * log_ret).sum(axis=1)
    turnover = (weights - weights.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS / 10_000.0
    return daily_pnl - cost


def compute_sharpe(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    r = returns.dropna()
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(periods_per_year))


def compute_dd(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 10] Multi-strategy ensemble portfolio — Sharpe 2.5 target analysis", flush=True)
    print("  Strategies : TSMOM 4etf + Crypto TSMOM + Sector Momentum + Bond/Gold TSMOM single + SPY benchmark",
          flush=True)
    print("  Weighting schemes : equal-weight / inverse-vol / risk-parity", flush=True)

    # 1) Compute all strategy returns
    print("[1/5] Computing strategy returns...", flush=True)
    etf = load_etf_panel()
    strat_returns = {}
    strat_returns["tsmom_4etf"] = compute_strat_tsmom_4etf(etf)
    strat_returns["crypto_tsmom"] = compute_strat_crypto_tsmom()
    strat_returns["sector_mom"] = compute_strat_sector_momentum()
    strat_returns["tsmom_tlt"] = compute_strat_single_tsmom(etf["TLT"])
    strat_returns["tsmom_gld"] = compute_strat_single_tsmom(etf["GLD"])
    strat_returns["spy_buyhold"] = etf["SPY"].pct_change()
    print(f"      Strategies : {list(strat_returns.keys())}", flush=True)

    # 2) Align on common dates
    print("[2/5] Aligning strategies on common date range...", flush=True)
    df_strats = pd.DataFrame(strat_returns).dropna()
    print(f"      Common period : {df_strats.index.min().date()} → {df_strats.index.max().date()}, "
          f"{len(df_strats)} days", flush=True)

    # 3) Individual Sharpes + correlation matrix
    print("[3/5] Individual Sharpes + correlation matrix...", flush=True)
    individual_sharpes = {col: compute_sharpe(df_strats[col]) for col in df_strats.columns}
    corr = df_strats.corr()
    print("      Individual Sharpes :", flush=True)
    for col, sh in individual_sharpes.items():
        print(f"        {col} : {sh:.3f}", flush=True)
    print("\n      Correlation matrix :", flush=True)
    print(corr.round(3).to_string(), flush=True)

    # 4) Portfolio combinations (excluding spy_buyhold from active strategies)
    active = [c for c in df_strats.columns if c != "spy_buyhold"]
    df_active = df_strats[active]

    # Equal-weight
    eq_pnl = df_active.mean(axis=1)
    eq_sharpe = compute_sharpe(eq_pnl)
    eq_dd = compute_dd(eq_pnl)

    # Inverse-vol (each strat's full-sample vol → weight)
    vols = df_active.std()
    inv_vol_w = (1 / vols) / (1 / vols).sum()
    inv_pnl = (df_active * inv_vol_w).sum(axis=1)
    inv_sharpe = compute_sharpe(inv_pnl)
    inv_dd = compute_dd(inv_pnl)

    # Risk-parity iterative (target: each strat contributes equal risk)
    cov = df_active.cov()
    n = len(active)
    w = np.ones(n) / n
    for _ in range(50):
        port_var = w @ cov.values @ w
        marginal = cov.values @ w
        risk_contrib = w * marginal
        target = port_var / n
        w = w * (target / risk_contrib) ** 0.5
        w = w / w.sum()
    rp_w = pd.Series(w, index=active)
    rp_pnl = (df_active * rp_w).sum(axis=1)
    rp_sharpe = compute_sharpe(rp_pnl)
    rp_dd = compute_dd(rp_pnl)

    print(f"\n[4/5] Portfolio Sharpes :", flush=True)
    print(f"      Equal-weight    : Sharpe {eq_sharpe:.3f}, DD {eq_dd*100:.1f}%", flush=True)
    print(f"      Inverse-vol     : Sharpe {inv_sharpe:.3f}, DD {inv_dd*100:.1f}%", flush=True)
    print(f"      Risk-parity     : Sharpe {rp_sharpe:.3f}, DD {rp_dd*100:.1f}%", flush=True)
    print(f"      Inv-vol weights : {inv_vol_w.round(3).to_dict()}", flush=True)
    print(f"      Risk-parity wt  : {rp_w.round(3).to_dict()}", flush=True)

    # Sub-sample
    mid = pd.Timestamp("2022-09-01")
    h1 = df_active[df_active.index < mid]
    h2 = df_active[df_active.index >= mid]
    eq_h1 = compute_sharpe(h1.mean(axis=1))
    eq_h2 = compute_sharpe(h2.mean(axis=1))
    inv_h1 = compute_sharpe((h1 * inv_vol_w).sum(axis=1))
    inv_h2 = compute_sharpe((h2 * inv_vol_w).sum(axis=1))
    rp_h1 = compute_sharpe((h1 * rp_w).sum(axis=1))
    rp_h2 = compute_sharpe((h2 * rp_w).sum(axis=1))
    print(f"\n      Sub-sample stability :", flush=True)
    print(f"      Equal h1={eq_h1:.2f} h2={eq_h2:.2f} Δ={abs(eq_h1-eq_h2):.2f}", flush=True)
    print(f"      InvVol h1={inv_h1:.2f} h2={inv_h2:.2f} Δ={abs(inv_h1-inv_h2):.2f}", flush=True)
    print(f"      RP h1={rp_h1:.2f} h2={rp_h2:.2f} Δ={abs(rp_h1-rp_h2):.2f}", flush=True)

    # Best portfolio decision
    best_name, best_sharpe, best_dd = max(
        [("equal-weight", eq_sharpe, eq_dd),
         ("inverse-vol", inv_sharpe, inv_dd),
         ("risk-parity", rp_sharpe, rp_dd)],
        key=lambda x: x[1]
    )
    best_dsub = abs([eq_h1-eq_h2, inv_h1-inv_h2, rp_h1-rp_h2][["equal-weight", "inverse-vol", "risk-parity"].index(best_name)])

    print(f"\n[5/5] Decision & verdict...", flush=True)
    if best_sharpe > 1.5 and abs(best_dd) < 0.25 and best_dsub < 0.5:
        decision = (f"Stage 1 PASS — Best portfolio {best_name} Sharpe {best_sharpe:.3f}, "
                    f"DD {best_dd*100:.1f}%, ΔSub {best_dsub:.2f}")
        emoji = "✅ STAGE 1 PASS"
    elif best_sharpe < 1.0:
        decision = (f"ARCHIVE — Best portfolio {best_name} Sharpe {best_sharpe:.3f} < 1.0, "
                    f"diversification benefit insuffisant")
        emoji = "🛑 ARCHIVE"
    else:
        decision = (f"Marginal — Best portfolio {best_name} Sharpe {best_sharpe:.3f}, "
                    f"DD {best_dd*100:.1f}%, ΔSub {best_dsub:.2f}. "
                    f"Sharpe 2.5 target NON-ATTEIGNABLE avec edges actuels (math: needs avg Sharpe ~1.0 × √(N/(1+(N-1)ρ)) "
                    f"avec ρ_avg={corr.values[np.triu_indices_from(corr.values, k=1)].mean():.2f}) → "
                    f"required ~10+ uncorrelated edges or higher individual Sharpes (paid data / niche markets)")
        emoji = "⚠️ MARGINAL — Sharpe 2.5 hors de portée free retail data"

    md_lines = []
    md_lines.append("# Cycle 10 — Multi-strategy ensemble portfolio (Sharpe 2.5 target analysis)")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v5 — Cycle 10 (final analysis Sharpe 2.5 path on free retail data)")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Individual strategy Sharpes")
    md_lines.append("")
    md_lines.append("| Strategy | Sharpe | β SPY | Notes |")
    md_lines.append("|---|---:|---|---|")
    for col, sh in individual_sharpes.items():
        md_lines.append(f"| {col} | {sh:.3f} | — | — |")
    md_lines.append("")
    md_lines.append("## Correlation matrix")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append(corr.round(3).to_string())
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("## Portfolio results (3 weighting schemes)")
    md_lines.append("")
    md_lines.append("| Scheme | Sharpe full | DD | ΔSub h1/h2 | Verdict gate |")
    md_lines.append("|---|---:|---:|---:|---|")
    md_lines.append(f"| Equal-weight | {eq_sharpe:.3f} | {eq_dd*100:.1f}% | {abs(eq_h1-eq_h2):.2f} | "
                     f"{'PASS' if (eq_sharpe>1.5 and abs(eq_dd)<0.25 and abs(eq_h1-eq_h2)<0.5) else 'FAIL'} |")
    md_lines.append(f"| Inverse-vol | {inv_sharpe:.3f} | {inv_dd*100:.1f}% | {abs(inv_h1-inv_h2):.2f} | "
                     f"{'PASS' if (inv_sharpe>1.5 and abs(inv_dd)<0.25 and abs(inv_h1-inv_h2)<0.5) else 'FAIL'} |")
    md_lines.append(f"| Risk-parity | {rp_sharpe:.3f} | {rp_dd*100:.1f}% | {abs(rp_h1-rp_h2):.2f} | "
                     f"{'PASS' if (rp_sharpe>1.5 and abs(rp_dd)<0.25 and abs(rp_h1-rp_h2)<0.5) else 'FAIL'} |")
    md_lines.append("")
    md_lines.append("## Portfolio weights")
    md_lines.append("")
    md_lines.append("| Strategy | Inv-vol weight | Risk-parity weight |")
    md_lines.append("|---|---:|---:|")
    for col in active:
        md_lines.append(f"| {col} | {inv_vol_w[col]:.3f} | {rp_w[col]:.3f} |")
    md_lines.append("")
    md_lines.append("## Sharpe 2.5 mathematical reachability")
    md_lines.append("")
    avg_sharpe = np.mean(list(individual_sharpes.values()))
    avg_corr = corr.values[np.triu_indices_from(corr.values, k=1)].mean()
    n_strats = len(active)
    md_lines.append(f"- **Average individual Sharpe** : {avg_sharpe:.3f}")
    md_lines.append(f"- **Average pairwise correlation** : {avg_corr:.3f}")
    md_lines.append(f"- **Theoretical portfolio Sharpe** = avg × √(N / (1 + (N-1)×ρ)) = "
                     f"{avg_sharpe:.2f} × √({n_strats}/{1 + (n_strats-1)*avg_corr:.2f}) = "
                     f"{avg_sharpe * np.sqrt(n_strats/(1+(n_strats-1)*avg_corr)):.3f}")
    md_lines.append("")
    md_lines.append(f"### Target Sharpe 2.5 reachability")
    md_lines.append("")
    md_lines.append(f"Pour atteindre Sharpe 2.5 avec individual edges ~Sharpe 1.0 :")
    for n_target in [5, 6, 8, 10, 12]:
        for rho_target in [0.0, 0.1, 0.2, 0.3]:
            theory = 1.0 * np.sqrt(n_target / (1 + (n_target - 1) * rho_target))
            mark = " ← Sharpe 2.5 atteint" if theory >= 2.5 else ""
            md_lines.append(f"- N={n_target} edges, ρ_avg={rho_target} → Sharpe portfolio ≈ {theory:.2f}{mark}")
        md_lines.append("")
    md_lines.append("### Conclusion realistique")
    md_lines.append("")
    md_lines.append(f"Avec {n_strats} edges actuels avg Sharpe {avg_sharpe:.2f} et ρ_avg {avg_corr:.2f}, ")
    md_lines.append(f"theoretical portfolio ceiling = {avg_sharpe * np.sqrt(n_strats/(1+(n_strats-1)*avg_corr)):.2f}.")
    md_lines.append(f"Sharpe 2.5 sur free retail data nécessite minimum 8-10 edges décorrélés (ρ<0.2) avec individual Sharpe >1.0.")
    md_lines.append(f"Path probable : ajouter trend-following non-equity (commodity futures via ETFs, FX), ")
    md_lines.append(f"carry strategies, event-driven discrets ; OU paid data ouvre VRP options + microstructure futures.")
    md_lines.append("")
    out_md = OUT_DIR / "cycle10_multistrat_ensemble_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    df_strats.to_parquet(OUT_DIR / "cycle10_strategies_returns.parquet")

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== Best portfolio : {best_name} Sharpe {best_sharpe:.3f}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
