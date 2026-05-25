"""run_cycle9_crypto_tsmom.py — R&D Cycle v5 / Cycle 9 Crypto TSMOM cross-asset.

Hypothèse pré-spec :
  Liu-Tsyvinski 2021 "Risks and Returns of Cryptocurrency" + Liu-Tsyvinski-Wu 2022 :
  cross-section crypto momentum + time-series momentum génèrent Sharpe ~2.0-2.5 sur
  2017-2020. Crypto market = jeune (< 15y), capacity-constrained, less institutional
  arbitrage que US equities. TSMOM Moskowitz/Ooi/Pedersen 2012 canonical (long si
  r_252d > 0 sinon cash, vol-target) appliqué à BTC/ETH/BNB/XRP/SOL.
  Forme falsifiable : Sharpe net > 1.5 + sub-sample stable (delta < 0.6) + max DD < 50%.

Anti-lookahead constraints :
  - r_252d strict past (calculate from t-252 to t-1 exclude current)
  - σ_60d past-only for vol-target
  - Signal at end-of-day t-1 → trade close t (1-day lag)

Asset universe :
  - BTC, ETH, BNB, XRP : 6.5y data 2019-06 → 2025-11
  - SOL : 5.5y data 2020-04 → 2025-11

Costs :
  - 10 bps RT per round-trip (Binance taker 4 bps × 2 + spread 2 bps)

Gates pré-écrits :
  - PROMOTE Stage 1 si Sharpe > 1.5 + DD < 50% + sub-sample ΔSharpe < 0.6
  - ARCHIVE si Sharpe < 0.7
  - ARCHIVE si DD > 70%
  - 1 amélioration K (lookback 365d ou 90d) si marginal
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = REPO_ROOT / "backend/data/short_interest"
DATA_PATH = REPO_ROOT / "backend/data/crypto/crypto_5coins_6.5y.parquet"

CRYPTO_TICKERS = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD"]
LOOKBACK_DAYS = 252
VOL_WINDOW_DAYS = 60
VOL_TARGET_ANN = 0.15  # 15% per asset (crypto vol higher than equities)
TRADING_DAYS_CRYPTO = 365  # crypto trades 7d/week
RT_BPS = 10  # 10 bps round-trip
SEED = 42


def load_crypto_prices(start: str = "2019-06-01", end: str = "2025-11-30") -> pd.DataFrame:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DATA_PATH.exists():
        df = pd.read_parquet(DATA_PATH)
        if df["date"].min() <= pd.Timestamp(start) and df["date"].max() >= pd.Timestamp(end):
            return df
    rows = []
    for sym in CRYPTO_TICKERS:
        d = yf.Ticker(sym).history(start=start, end=end, auto_adjust=False)
        d = d[["Close", "Adj Close"]].reset_index()
        d.columns = ["date", "close", "adj_close"]
        d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)
        d["symbol"] = sym.replace("-USD", "")
        rows.append(d)
    df = pd.concat(rows, ignore_index=True)
    df.to_parquet(DATA_PATH, index=False)
    return df


def compute_tsmom_signal(df: pd.DataFrame, lookback: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """For each (symbol, date), compute long-cash signal based on past lookback returns.

    Anti-lookahead : signal at t-1 (uses returns t-1-lookback to t-1).
    """
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    out_rows = []
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("date").reset_index(drop=True)
        # Past return r_lookback : end exclusive at t-1
        # signal_t uses prices[t-lookback-1 : t-1]
        g["price_past"] = g["adj_close"].shift(lookback)
        g["price_lag1"] = g["adj_close"].shift(1)
        g["r_lookback"] = (g["price_lag1"] / g["price_past"]) - 1
        g["signal"] = (g["r_lookback"] > 0).astype(int)
        # Vol estimate from lagged returns
        g["log_ret"] = np.log(g["adj_close"]).diff()
        g["vol_60d"] = g["log_ret"].shift(1).rolling(VOL_WINDOW_DAYS, min_periods=VOL_WINDOW_DAYS).std()
        g["vol_60d_ann"] = g["vol_60d"] * np.sqrt(TRADING_DAYS_CRYPTO)
        # Vol-target weight : capped at 1.0 (no leverage)
        g["weight"] = np.where(
            g["vol_60d_ann"] > 0,
            np.minimum(VOL_TARGET_ANN / g["vol_60d_ann"], 1.0),
            0.0,
        )
        g["weight"] = g["weight"] * g["signal"]
        out_rows.append(g)
    return pd.concat(out_rows, ignore_index=True)


def simulate_portfolio(df: pd.DataFrame, rt_bps: float = RT_BPS) -> pd.DataFrame:
    """Equal-weight long-only TSMOM portfolio across 5 cryptos.

    Daily PnL = sum_i (weight_i × log_ret_i / N_active)
    Costs : per-asset turnover cost when weight changes day-over-day.
    """
    pivot_w = df.pivot(index="date", columns="symbol", values="weight").sort_index()
    pivot_r = df.pivot(index="date", columns="symbol", values="log_ret").sort_index()
    pivot_w = pivot_w.fillna(0.0)
    pivot_r = pivot_r.fillna(0.0)

    # Equal-weight across active assets : each asset gets weight_i / sum(active)
    # Or simpler : weight_i / N (constant denominator)
    n_assets = pivot_w.shape[1]
    portfolio_w = pivot_w / n_assets

    # Daily PnL : sum_i (portfolio_w_i × log_ret_i) — using log returns ≈ simple at small returns
    daily_pnl = (portfolio_w.shift(1) * pivot_r).sum(axis=1)  # weight shift +1 = anti-lookahead
    # Turnover cost : delta in absolute weights
    turnover = (portfolio_w - portfolio_w.shift(1)).abs().sum(axis=1)
    cost = turnover * rt_bps / 10_000.0
    daily_pnl_net = daily_pnl - cost

    return pd.DataFrame({
        "date": daily_pnl_net.index,
        "pnl_gross": daily_pnl.values,
        "pnl_net": daily_pnl_net.values,
        "turnover": turnover.values,
        "n_active": (portfolio_w.shift(1) > 0).sum(axis=1).values,
    })


def compute_sharpe(returns: np.ndarray, periods_per_year: int = TRADING_DAYS_CRYPTO) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(periods_per_year))


def compute_dd_calmar(returns: np.ndarray, periods_per_year: int = TRADING_DAYS_CRYPTO
                       ) -> tuple[float, float, float]:
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    eq = np.cumprod(1 + r)
    cagr = eq[-1] ** (periods_per_year / len(r)) - 1
    rmax = np.maximum.accumulate(eq)
    dd = (eq - rmax) / rmax
    return float(cagr), float(dd.min()), float(cagr / abs(dd.min()) if dd.min() < 0 else 0.0)


def beta_vs_spy(returns: np.ndarray, dates: pd.Series) -> float:
    """Compute β to SPY (using SP500 prices parquet)."""
    spy_path = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
    df_spy = pd.read_parquet(spy_path)[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["spy_adj"].pct_change()
    pair = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    if len(merged) < 10:
        return 0.0
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    return float(cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0.0)


def permutation_test(returns: np.ndarray, signals: np.ndarray, n_iter: int = 500,
                       seed: int = SEED) -> tuple[float, float]:
    """Shuffle signal sequence keeping return sequence intact, compare Sharpe.

    Note : Hjalmarsson 2011 montre que bar permutation est conservative pour trend-following
    long-only avec drift. Inclus pour transparence mais pas gate pré-écrit ici car
    crypto n'a pas drift positif aussi clair que SP500 long-term.
    """
    rng = np.random.RandomState(seed)
    real = compute_sharpe(returns * signals)
    shuffled = []
    for _ in range(n_iter):
        permuted = rng.permutation(signals)
        shuffled.append(compute_sharpe(returns * permuted))
    shuffled = np.array(shuffled)
    p_value = float((shuffled >= real).mean())
    return real, p_value


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 9] Crypto TSMOM cross-asset 5 coins", flush=True)
    print(f"  Universe: BTC + ETH + BNB + XRP + SOL", flush=True)
    print(f"  TSMOM Moskowitz canonical : long if r_{LOOKBACK_DAYS}d > 0 else cash, "
          f"vol-target {VOL_TARGET_ANN*100:.0f}% per asset, equal-weight", flush=True)
    print(f"  Anti-lookahead : signal t-1 → trade close t", flush=True)
    print(f"  Costs : {RT_BPS} bps RT, {TRADING_DAYS_CRYPTO} days/year crypto", flush=True)

    print("[1/4] Loading crypto prices...", flush=True)
    df = load_crypto_prices()
    print(f"      Total rows : {len(df)}, symbols : {sorted(df['symbol'].unique())}", flush=True)

    print(f"[2/4] Computing TSMOM signal (lookback {LOOKBACK_DAYS}d, vol-window {VOL_WINDOW_DAYS}d)...",
          flush=True)
    df = compute_tsmom_signal(df)

    print("[3/4] Simulating portfolio...", flush=True)
    sim = simulate_portfolio(df)
    perf_start = LOOKBACK_DAYS + VOL_WINDOW_DAYS + 1
    perf = sim.iloc[perf_start:].reset_index(drop=True)

    print("[4/4] Computing metrics...", flush=True)
    sharpe = compute_sharpe(perf["pnl_net"].values)
    sharpe_gross = compute_sharpe(perf["pnl_gross"].values)
    cagr, dd, calmar = compute_dd_calmar(perf["pnl_net"].values)
    beta_spy = beta_vs_spy(perf["pnl_net"].values, perf["date"])
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid]
    h2 = perf[perf["date"] >= mid]
    sh_h1 = compute_sharpe(h1["pnl_net"].values)
    sh_h2 = compute_sharpe(h2["pnl_net"].values)
    delta_sub = abs(sh_h1 - sh_h2)

    # Permutation test (transparency only, not gate)
    pivot_w = df.pivot(index="date", columns="symbol", values="weight").sort_index().fillna(0.0)
    pivot_r = df.pivot(index="date", columns="symbol", values="log_ret").sort_index().fillna(0.0)
    n_assets = pivot_w.shape[1]
    portfolio_w = (pivot_w / n_assets).iloc[perf_start:]
    portfolio_r = pivot_r.iloc[perf_start:]
    # Aggregate to portfolio level
    avg_signal = (portfolio_w > 0).any(axis=1).astype(int)
    avg_pnl = (portfolio_w.shift(1) * portfolio_r).sum(axis=1).iloc[1:].values
    real_sh, perm_p = permutation_test(avg_pnl, avg_signal.shift(1).fillna(0).iloc[1:].values, n_iter=500)

    print(f"      Sharpe (gross) = {sharpe_gross:.3f}", flush=True)
    print(f"      Sharpe (net) = {sharpe:.3f}", flush=True)
    print(f"      CAGR = {cagr*100:.2f}%, MaxDD = {dd*100:.2f}%, Calmar = {calmar:.2f}", flush=True)
    print(f"      |β SPY| = {abs(beta_spy):.4f}", flush=True)
    print(f"      Sub-sample h1 = {sh_h1:.3f}, h2 = {sh_h2:.3f}, Δ = {delta_sub:.3f}", flush=True)
    print(f"      Permutation p-value (info only) = {perm_p:.4f}", flush=True)

    # Decision
    archive = []
    if sharpe < 0.7:
        archive.append(f"Sharpe net {sharpe:.3f} < 0.7")
    if abs(dd) > 0.70:
        archive.append(f"MaxDD {dd*100:.1f}% > 70%")
    if delta_sub > 0.6:
        archive.append(f"ΔSharpe sub {delta_sub:.2f} > 0.6")
    if archive:
        decision = "ARCHIVE — " + " ; ".join(archive)
        emoji = "🛑 ARCHIVE"
    elif sharpe > 1.5 and abs(dd) < 0.50 and delta_sub < 0.6:
        decision = ("Stage 1 PASS — Crypto TSMOM débloque edge multi-asset cross-asset, "
                    "Sharpe target 2.5 atteignable via portfolio combination")
        emoji = "✅ STAGE 1 PASS"
    else:
        decision = (f"Marginal (Sharpe {sharpe:.3f}, DD {dd*100:.1f}%, Δsub {delta_sub:.2f}) — "
                    f"borderline, considérer pour portfolio combination Cycle 10 mais pas "
                    f"individual edge product-grade")
        emoji = "⚠️ MARGINAL"

    md_lines = []
    md_lines.append("# Cycle 9 — Crypto TSMOM cross-asset 5 coins")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v5 — Cycle 9 (target Sharpe 2.5 path)")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : Liu-Tsyvinski 2021 + Liu-Tsyvinski-Wu 2022 — crypto market jeune <15y, "
                     f"capacity-constrained, less institutional arbitrage que US equities. Time-series momentum "
                     f"Moskowitz canonical (12-month lookback, vol-target) sur BTC/ETH/BNB/XRP/SOL = "
                     f"Sharpe 2.0-2.5 documenté académique 2017-2020.")
    md_lines.append(f"- **Univers** : BTC + ETH + BNB + XRP (2019-06 → 2025-11), SOL (2020-04 → 2025-11)")
    md_lines.append(f"- **Lookback** : {LOOKBACK_DAYS}d (TSMOM canonical)")
    md_lines.append(f"- **Vol-target** : {VOL_TARGET_ANN*100:.0f}% per asset (crypto vol >> equity), capped 1× (no leverage)")
    md_lines.append(f"- **Costs** : {RT_BPS} bps RT (Binance taker 4×2 + spread 2 bps)")
    md_lines.append(f"- **Anti-lookahead** : signal at t-1 (lookback strict past) → trade close t")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe gross | {sharpe_gross:.3f} |")
    md_lines.append(f"| Sharpe net | {sharpe:.3f} |")
    md_lines.append(f"| CAGR net | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} |")
    md_lines.append(f"| Sub-sample h1 (avant 2022-09) | {sh_h1:.3f} |")
    md_lines.append(f"| Sub-sample h2 (après 2022-09) | {sh_h2:.3f} |")
    md_lines.append(f"| ΔSharpe sub-sample | {delta_sub:.3f} |")
    md_lines.append(f"| Permutation p-value (info) | {perm_p:.4f} |")
    md_lines.append("")
    md_lines.append("## Diagnostic gates")
    md_lines.append("")
    md_lines.append(f"| Gate | Result | Status |")
    md_lines.append(f"|---|---|---|")
    md_lines.append(f"| Sharpe net > 1.5 | {sharpe:.3f} | {'PASS' if sharpe > 1.5 else 'FAIL'} |")
    md_lines.append(f"| Sharpe net > 0.7 | {sharpe:.3f} | {'PASS' if sharpe > 0.7 else 'FAIL'} |")
    md_lines.append(f"| Max DD < 50% | {dd*100:.1f}% | {'PASS' if abs(dd) < 0.50 else 'FAIL'} |")
    md_lines.append(f"| ΔSharpe sub-sample < 0.6 | {delta_sub:.2f} | "
                     f"{'PASS' if delta_sub < 0.6 else 'FAIL'} |")
    md_lines.append("")
    out_md = OUT_DIR / "cycle9_crypto_tsmom_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_parquet(OUT_DIR / "cycle9_crypto_tsmom_pnl.parquet", index=False)
    df.to_parquet(OUT_DIR / "cycle9_crypto_tsmom_signals.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
