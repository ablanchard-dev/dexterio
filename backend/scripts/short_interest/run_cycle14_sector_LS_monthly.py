"""run_cycle14_sector_LS_monthly.py — R&D Cycle v6 / Cycle 14 Sector Long-Short cross-sectional MONTHLY decile.

Hypothèse pré-spec :
  Asness 1997 + Moskowitz 1999 cross-sectional momentum proper construction :
  monthly rebalance, long top-decile / short bottom-decile, dollar-neutral, hold 1 month.
  Cycle 12 a testé Top-3 LONG ONLY (Sharpe 0.41). Ici LONG-SHORT proper avec full universe
  diversification + market-neutral.

Universe : 11 SPDR sector ETFs (XLF, XLE, XLK, XLY, XLP, XLI, XLB, XLU, XLV, XLRE, XLC).

Anti-lookahead :
  - 6-month return signal computed at end of month t-1
  - Apply rebalance at open month t
  - Hold full month, exit at end month t

Costs : 3 bps RT × turnover (entries + exits each rebalance)

Gates pré-écrits :
  - PROMOTE Stage 1 si Sharpe net > 1.2 + |β SPY|<0.1 + ΔSub<0.4
  - ARCHIVE si Sharpe < 0.5
  - Long-only top-3 baseline Cycle 12 = 0.41 → must beat with substantial lift
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SECTORS_PATH = REPO_ROOT / "backend/data/equities/sectors_11_prices_6.5y.parquet"
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"

LOOKBACK_DAYS = 126  # 6-month canonical
TOP_N = 3  # top 3, bottom 3 (out of 11)
RT_BPS = 3
TRADING_DAYS = 252


def load_sector_prices():
    df = pd.read_parquet(SECTORS_PATH)
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    return pivot.dropna()


def get_month_ends(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Last trading day of each month (signal timing)."""
    df = pd.DataFrame(index=dates)
    df["month"] = df.index.to_period("M")
    return [g.index[-1] for _, g in df.groupby("month")]


def get_month_starts(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """First trading day of each month (rebalance timing)."""
    df = pd.DataFrame(index=dates)
    df["month"] = df.index.to_period("M")
    return [g.index[0] for _, g in df.groupby("month")]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 14] Sector Long-Short cross-sectional MONTHLY decile", flush=True)
    print(f"  11 SPDR sectors, lookback {LOOKBACK_DAYS}d, top/bottom {TOP_N} L/S", flush=True)

    print("[1/4] Loading sector prices...", flush=True)
    prices = load_sector_prices()
    print(f"      Shape : {prices.shape}, sectors : {list(prices.columns)}", flush=True)

    print("[2/4] Computing 6-month returns at month-end signals...", flush=True)
    month_ends = get_month_ends(prices.index)
    month_starts = get_month_starts(prices.index)
    log_ret = np.log(prices).diff()

    # Signal date = last trading day of month t-1, applied at first trading day of month t
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for i, signal_date in enumerate(month_ends[:-1]):
        # Need lookback worth of data
        idx = prices.index.get_loc(signal_date)
        if idx < LOOKBACK_DAYS:
            continue
        # 6-month return from signal_date - LOOKBACK_DAYS to signal_date
        past_return = (prices.iloc[idx] / prices.iloc[idx - LOOKBACK_DAYS]) - 1
        ranks = past_return.rank(ascending=False)
        long_set = ranks[ranks <= TOP_N].index.tolist()
        short_set = ranks[ranks > (len(ranks) - TOP_N)].index.tolist()
        # Apply rebalance from month_starts[i+1] until next signal date
        if i + 1 < len(month_starts):
            apply_start = month_starts[i + 1]
            apply_end = month_ends[i + 1] if i + 1 < len(month_ends) else prices.index[-1]
            mask = (prices.index >= apply_start) & (prices.index <= apply_end)
            for sym in long_set:
                weights.loc[mask, sym] = 1.0 / len(long_set)
            for sym in short_set:
                weights.loc[mask, sym] = -1.0 / len(short_set)

    print("[3/4] Simulating PnL...", flush=True)
    daily_pnl = (weights.shift(1) * log_ret).sum(axis=1)
    turnover = (weights - weights.shift(1)).abs().sum(axis=1)
    cost = turnover * RT_BPS / 10_000.0
    pnl_net = daily_pnl - cost

    perf_start = LOOKBACK_DAYS + 21
    perf = pnl_net.iloc[perf_start:]

    print("[4/4] Metrics...", flush=True)
    sharpe = (perf.mean() / perf.std()) * np.sqrt(TRADING_DAYS)
    eq = (1 + perf).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / len(perf)) - 1
    rmax = eq.cummax()
    dd = (eq - rmax) / rmax
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    # Sub-sample
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf.index < mid]
    h2 = perf[perf.index >= mid]
    sh_h1 = (h1.mean() / h1.std()) * np.sqrt(TRADING_DAYS)
    sh_h2 = (h2.mean() / h2.std()) * np.sqrt(TRADING_DAYS)
    delta_sub = abs(sh_h1 - sh_h2)
    # Beta SPY
    df_spy = pd.read_parquet(SPY_PATH)[["date", "Adj Close"]]
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["Adj Close"].pct_change()
    pair = pd.DataFrame({"date": perf.index.values, "ret": perf.values})
    merged = pair.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    beta_spy = float(cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0)

    print(f"      Sharpe = {sharpe:.3f}, CAGR = {cagr*100:+.2f}%, MaxDD = {max_dd*100:.2f}%", flush=True)
    print(f"      Calmar = {calmar:.2f}, β SPY = {beta_spy:+.4f}", flush=True)
    print(f"      Sub-sample h1/h2 = {sh_h1:.3f}/{sh_h2:.3f} (Δ={delta_sub:.3f})", flush=True)

    # Decision
    if sharpe > 1.2 and abs(beta_spy) < 0.1 and delta_sub < 0.4:
        decision = f"Stage 1 PASS — Sector LS decile monthly Sharpe {sharpe:.3f} market-neutral robust"
        emoji = "✅ STAGE 1 PASS"
    elif sharpe > 0.7 and abs(beta_spy) < 0.2:
        decision = f"Marginal-good — Sharpe {sharpe:.3f}, β {beta_spy:+.3f} useful for ensemble"
        emoji = "⚠️ MARGINAL"
    elif sharpe < 0.5:
        decision = f"ARCHIVE — Sharpe {sharpe:.3f} < 0.5"
        emoji = "🛑 ARCHIVE"
    else:
        decision = f"Marginal — Sharpe {sharpe:.3f}, ARCHIVE strict per discipline"
        emoji = "🛑 ARCHIVE (marginal)"

    md_lines = []
    md_lines.append("# Cycle 14 — Sector L/S cross-sectional monthly decile")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net | **{sharpe:.3f}** |")
    md_lines.append(f"| CAGR | {cagr*100:+.2f}% |")
    md_lines.append(f"| Max DD | {max_dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY (market-neutral target ~0) | {beta_spy:+.4f} |")
    md_lines.append(f"| Sub-sample h1/h2 | {sh_h1:.3f}/{sh_h2:.3f} (Δ={delta_sub:.3f}) |")
    md_lines.append("")
    md_lines.append("## Comparison vs S+3 T2 Sector Mom long-only top-3")
    md_lines.append("")
    md_lines.append("| Variant | Sharpe | β SPY |")
    md_lines.append("|---|---:|---:|")
    md_lines.append("| S+3 T2 Top-3 LONG ONLY (daily rebal) | 0.66 | high (long-equity) |")
    md_lines.append("| Cycle 10 sector_mom recompute (daily) | 0.42 | high |")
    md_lines.append(f"| **Cycle 14 Top-3/Bot-3 LS MONTHLY decile** | {sharpe:.3f} | {beta_spy:+.3f} |")
    out_md = OUT_DIR / "cycle14_sector_LS_monthly_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    pnl_net.to_frame("pnl").to_parquet(OUT_DIR / "cycle14_sector_LS_pnl.parquet")
    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Sharpe : {sharpe:.3f} | {emoji}", flush=True)


if __name__ == "__main__":
    main()
