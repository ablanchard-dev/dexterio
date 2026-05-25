"""run_cycle6_johansen_multivariate.py — R&D Cycle v3 / Cycle 6 Johansen multivariate cointegration.

Hypothèse pré-spec :
  Johansen 1988 "Statistical Analysis of Cointegration Vectors" : test multivariate
  permet de trouver baskets cointégrés de 3+ assets (extension de Engle-Granger 2-asset).
  Pour chaque basket, l'eigenvector cointégrant donne des poids → spread mean-reverting
  → mean-reversion strategy sur la composante d'écart.
  Forme falsifiable : Sharpe net > 0.6 + |β SPY| < 0.1 + ΔSharpe sub-sample < 0.4 + half-life 5-30d.

Anti-lookahead constraints :
  - Johansen test fit sur fenêtre rolling 252d strictement < t
  - Eigenvector cointégrant utilisé pour t (pas re-fit sur full sample)
  - Z-score spread rolling 60d past-only
  - Signal at close t-1 → trade close t (shift)

Baskets pré-spec (testés indépendamment) :
  1. **Big banks** : JPM + BAC + WFC + C (4 names)
  2. **Payment networks** : MA + V + AXP + DFS (4 names)
  3. **Energy majors** : XOM + CVX + COP + EOG (4 names)

Gates pré-écrits :
  - PROMOTE Stage 1 si ≥1 basket Sharpe > 0.7 + |β SPY|<0.1 + ΔSharpe sub<0.4 + half-life 5-30d
  - ARCHIVE basket si Sharpe < 0.5 OR |β SPY| > 0.2
  - Verdict global : PASS si ≥1/3 baskets PASS, ARCHIVE si 0/3
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

JOHANSEN_WINDOW = 252
ZSCORE_WINDOW = 60
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 3.5
RT_BPS_PER_LEG = 10
TRADING_DAYS = 252

BASKETS = {
    "big_banks": ["JPM", "BAC", "WFC", "C"],
    "payments": ["MA", "V", "AXP", "COF"],  # DFS pas dans parquet, COF (Capital One) substitut payments/cards
    "energy_majors": ["XOM", "CVX", "COP", "EOG"],
}


def load_basket_prices(symbols: list[str]) -> pd.DataFrame:
    """Load adjusted prices for a basket from SP500 parquet."""
    df = pd.read_parquet(SP500_PRICES_PATH)
    df = df[df["symbol"].isin(symbols)][["date", "symbol", "adj_close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    pivot = pivot.dropna()
    return pivot[symbols]  # ensure column order matches input


def rolling_johansen_spread(log_prices: pd.DataFrame,
                              window: int = JOHANSEN_WINDOW) -> pd.DataFrame:
    """Rolling Johansen fit, extract first cointegrating vector, project spread.

    For each day t starting at window:
      - Fit Johansen on log_prices[t-window : t] (past only)
      - Extract first eigenvector (largest eigenvalue → most stable cointegration)
      - Spread_t = log_prices_t @ eigenvector
    """
    n = len(log_prices)
    spread = pd.Series(index=log_prices.index, dtype=float)
    eigvecs = pd.DataFrame(index=log_prices.index, columns=log_prices.columns, dtype=float)
    for i in range(window, n):
        past = log_prices.iloc[i - window:i].values
        try:
            result = coint_johansen(past, det_order=0, k_ar_diff=1)
            eigvec = result.evec[:, 0]  # first (largest eigenvalue)
            # Normalize so first element is +1 for interpretability
            if eigvec[0] != 0:
                eigvec = eigvec / eigvec[0]
            current = log_prices.iloc[i].values
            spread.iloc[i] = float(np.dot(current, eigvec))
            for j, sym in enumerate(log_prices.columns):
                eigvecs.iloc[i, j] = eigvec[j]
        except Exception:
            continue
    return spread, eigvecs


def compute_zscore_past(spread: pd.Series, window: int = ZSCORE_WINDOW) -> pd.Series:
    """Rolling z-score past-only (excludes current point)."""
    mean = spread.rolling(window, min_periods=window).mean().shift(1)
    std = spread.rolling(window, min_periods=window).std().shift(1)
    return (spread - mean) / std


def simulate_pair_trades(prices: pd.DataFrame, spread: pd.Series, z: pd.Series,
                            eigvecs: pd.DataFrame,
                            entry: float, exit_: float, stop: float,
                            bps_per_leg: float) -> pd.DataFrame:
    """Simulate Johansen-basket pair trades. Position weights = ±eigenvector at entry, frozen."""
    n = len(prices)
    daily_pnl = np.zeros(n)
    side = np.zeros(n, dtype=int)
    position = 0
    weights_entry = np.zeros(prices.shape[1])
    for i in range(1, n):
        z_yesterday = z.iloc[i - 1]
        if position != 0:
            today_ret = prices.iloc[i] / prices.iloc[i - 1] - 1
            # PnL = sum_j (weight_j * stock_j_ret) * position_sign
            # We use eigenvector at entry as weights (frozen for the duration of trade)
            day_pnl = position * float(np.sum(weights_entry * today_ret.values))
            daily_pnl[i] = day_pnl
            side[i] = position
        if position == 0:
            if not np.isnan(z_yesterday):
                if z_yesterday > entry:
                    # Spread positive → short the spread (eigenvector tilt to the negative side)
                    position = -1
                    weights_entry = eigvecs.iloc[i - 1].values
                    daily_pnl[i] -= bps_per_leg * len(prices.columns) / 10_000.0
                elif z_yesterday < -entry:
                    # Spread negative → long the spread
                    position = +1
                    weights_entry = eigvecs.iloc[i - 1].values
                    daily_pnl[i] -= bps_per_leg * len(prices.columns) / 10_000.0
        else:
            # Currently in position → check exit/stop using z[t-1]
            should_exit = False
            if not np.isnan(z_yesterday):
                if abs(z_yesterday) < exit_:
                    should_exit = True
                elif abs(z_yesterday) > stop:
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


def beta_vs_spy(returns: np.ndarray, dates: pd.Series) -> float:
    df_spy = pd.read_parquet(SPY_PATH)[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
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


def evaluate_basket(name: str, symbols: list[str], out_dir: Path) -> dict:
    print(f"  >> Basket {name} : {symbols}", flush=True)
    prices = load_basket_prices(symbols)
    if prices.empty or len(prices) < JOHANSEN_WINDOW + ZSCORE_WINDOW + 100:
        return {"name": name, "symbols": symbols, "status": "INSUFFICIENT_DATA",
                  "n_days": len(prices)}
    log_prices = np.log(prices)
    spread, eigvecs = rolling_johansen_spread(log_prices, JOHANSEN_WINDOW)
    z = compute_zscore_past(spread, ZSCORE_WINDOW)
    perf_start = JOHANSEN_WINDOW + ZSCORE_WINDOW
    sim = simulate_pair_trades(prices, spread, z, eigvecs,
                                  entry=ENTRY_Z, exit_=EXIT_Z, stop=STOP_Z,
                                  bps_per_leg=RT_BPS_PER_LEG)
    perf = sim.iloc[perf_start:].reset_index(drop=True)
    sharpe = compute_sharpe(perf["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar(perf["pnl"].values)
    beta_spy = beta_vs_spy(perf["pnl"].values, perf["date"])
    hl = half_life_ou(spread.iloc[perf_start:])
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid]
    h2 = perf[perf["date"] >= mid]
    sh_h1 = compute_sharpe(h1["pnl"].values)
    sh_h2 = compute_sharpe(h2["pnl"].values)
    delta_sub = abs(sh_h1 - sh_h2)
    n_trades = int((sim["side"].diff().fillna(0).abs() > 0).sum() // 2)

    archive: list[str] = []
    if sharpe < 0.5:
        archive.append(f"Sharpe {sharpe:.3f} < 0.5")
    if abs(beta_spy) > 0.2:
        archive.append(f"|β SPY| {abs(beta_spy):.3f} > 0.2")
    if delta_sub > 0.5:
        archive.append(f"ΔSharpe sub {delta_sub:.2f} > 0.5")
    if not (5 <= hl <= 30):
        if not np.isnan(hl):
            archive.append(f"half-life {hl:.1f}d outside [5, 30]")
    if archive:
        verdict = "ARCHIVE — " + " ; ".join(archive)
        emoji = "🛑"
    elif sharpe > 0.7 and abs(beta_spy) < 0.1 and delta_sub < 0.4 and 5 <= hl <= 30:
        verdict = "Stage 1 PASS"
        emoji = "✅"
    else:
        verdict = f"Marginal — ARCHIVE strict (Sharpe {sharpe:.3f}, |β|={abs(beta_spy):.3f})"
        emoji = "🛑"

    print(f"     {emoji} Sharpe {sharpe:.3f} | β SPY {beta_spy:+.4f} | hl {hl:.1f}d | "
          f"Δsub {delta_sub:.2f} | n_trades {n_trades} → {verdict}", flush=True)

    perf.to_parquet(out_dir / f"cycle6_johansen_{name}_pnl.parquet", index=False)
    return {
        "name": name,
        "symbols": symbols,
        "n_days_perf": len(perf),
        "sharpe": sharpe,
        "cagr": cagr,
        "max_dd": dd,
        "calmar": calmar,
        "beta_spy": beta_spy,
        "half_life": hl,
        "delta_subsample": delta_sub,
        "sharpe_h1": sh_h1,
        "sharpe_h2": sh_h2,
        "n_trades": n_trades,
        "verdict": verdict,
        "emoji": emoji,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[Cycle 6] Johansen multivariate cointegration — 3 baskets", flush=True)
    print(f"  Window 2019-06 → 2025-11 (6.5y), Johansen rolling {JOHANSEN_WINDOW}d", flush=True)
    print(f"  Anti-lookahead : eigenvector past-only, z-score past-only, signal shifted t+1", flush=True)
    print(f"  Costs : {RT_BPS_PER_LEG} bps/leg, entry |z|>{ENTRY_Z}, exit |z|<{EXIT_Z}, stop |z|>{STOP_Z}", flush=True)

    results = []
    for name, symbols in BASKETS.items():
        result = evaluate_basket(name, symbols, args.out_dir)
        results.append(result)

    # Aggregate verdict
    n_pass = sum(1 for r in results if r.get("emoji") == "✅")
    if n_pass >= 1:
        global_verdict = (f"Stage 1 PASS — {n_pass}/3 baskets passed all gates → multivariate "
                            f"cointegration approach validated on at least 1 cointegrated basket")
        global_emoji = "✅ STAGE 1 PASS"
    else:
        global_verdict = "ARCHIVE — 0/3 baskets passed (multivariate cointegration ne débloque pas edge sur baskets testés)"
        global_emoji = "🛑 ARCHIVE"

    md_lines: list[str] = []
    md_lines.append("# Cycle 6 — Johansen multivariate cointegration")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v3 — Cycle 6")
    md_lines.append("")
    md_lines.append(f"## Decision globale : {global_emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {global_verdict}")
    md_lines.append("")
    md_lines.append("## Méthodologie")
    md_lines.append("")
    md_lines.append(f"- **Source** : Johansen 1988 \"Statistical Analysis of Cointegration Vectors\"")
    md_lines.append(f"- **Test** : `statsmodels.tsa.vector_ar.vecm.coint_johansen` rolling {JOHANSEN_WINDOW}d "
                     f"past-only, det_order=0, k_ar_diff=1")
    md_lines.append(f"- **Spread** : log_prices @ first eigenvector (largest eigenvalue, most stable coint)")
    md_lines.append(f"- **Z-score** : rolling {ZSCORE_WINDOW}d past-only (shift 1)")
    md_lines.append(f"- **Trade** : entry |z|>{ENTRY_Z}, exit |z|<{EXIT_Z}, stop |z|>{STOP_Z}, "
                     f"weights = eigenvector frozen at entry")
    md_lines.append(f"- **Anti-lookahead** : Johansen fit past-only, signal at z[t-1] → trade close t")
    md_lines.append(f"- **Costs** : {RT_BPS_PER_LEG} bps × n_assets per round-trip (turnover-aware)")
    md_lines.append("")
    md_lines.append("## Per-basket results")
    md_lines.append("")
    md_lines.append("| Basket | Symbols | Sharpe | β SPY | half-life | Δsub | n_trades | Verdict |")
    md_lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for r in results:
        if r.get("status") == "INSUFFICIENT_DATA":
            md_lines.append(f"| {r['name']} | {','.join(r['symbols'])} | — | — | — | — | — | INSUFFICIENT_DATA |")
            continue
        md_lines.append(f"| {r['name']} | {','.join(r['symbols'])} | "
                         f"{r['sharpe']:.3f} | {r['beta_spy']:+.4f} | {r['half_life']:.1f}d | "
                         f"{r['delta_subsample']:.2f} | {r['n_trades']} | {r['emoji']} {r['verdict']} |")
    md_lines.append("")
    md_lines.append("## Per-basket detail")
    md_lines.append("")
    for r in results:
        if r.get("status") == "INSUFFICIENT_DATA":
            continue
        md_lines.append(f"### {r['name']} ({', '.join(r['symbols'])})")
        md_lines.append("")
        md_lines.append(f"| Métrique | Valeur |")
        md_lines.append(f"|---|---:|")
        md_lines.append(f"| Sharpe net | {r['sharpe']:.3f} |")
        md_lines.append(f"| CAGR | {r['cagr']*100:.2f}% |")
        md_lines.append(f"| Max DD | {r['max_dd']*100:.2f}% |")
        md_lines.append(f"| Calmar | {r['calmar']:.2f} |")
        md_lines.append(f"| β SPY | {r['beta_spy']:+.4f} |")
        md_lines.append(f"| Half-life OU | {r['half_life']:.1f}d |")
        md_lines.append(f"| Sub-sample h1/h2 (split 2022-09-01) | h1={r['sharpe_h1']:.2f}, h2={r['sharpe_h2']:.2f}, Δ={r['delta_subsample']:.2f} |")
        md_lines.append(f"| n trades | {r['n_trades']} |")
        md_lines.append("")

    out_md = args.out_dir / "cycle6_johansen_multivariate_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n=== Verdict global → {out_md}", flush=True)
    print(f"=== {global_emoji} : {global_verdict}", flush=True)


if __name__ == "__main__":
    main()
