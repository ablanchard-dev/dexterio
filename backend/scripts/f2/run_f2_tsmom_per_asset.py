"""F2 TSMOM per-asset Sharpe individuel — Priority #1 plan v4.0 J2.2.

Run TSMOM signal **per asset solo** (long si r_252 > 0 sinon cash) sur SPY,
QQQ, GLD, TLT individuellement. Reporte Sharpe + CAGR + max DD + % time long.

Gate plan : ≥3/4 actifs avec Sharpe individuel > 0.5 = PASS.
Kill rule : <2/4 actifs avec Sharpe > 0.4 → ARCHIVE TSMOM.

Pourquoi : un Sharpe portfolio 0.96 pourrait être porté par 1 asset chanceux.
Per-asset gate vérifie que l'edge tient sur ≥3 marchés indépendants
(condition canonique TSMOM Moskowitz : edge cross-asset, pas single-asset luck).

Usage : python backend/scripts/f2/run_f2_tsmom_per_asset.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.portfolio.allocator import PortfolioAllocator
from engines.portfolio.backtester import buy_and_hold, run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "GLD", "TLT"]


def load_prices(tickers):
    frames = []
    for t in tickers:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def sharpe_ann(r):
    r = r.dropna()
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def main() -> None:
    prices_all = load_prices(TICKERS)
    print(f"Corpus : {prices_all.index[0].date()} → {prices_all.index[-1].date()} "
          f"({len(prices_all)} days)")
    print()

    print(f"{'Ticker':<8} {'BH_Sharpe':>10} {'TSMOM_Sharpe':>14} {'TSMOM_CAGR':>12} "
          f"{'TSMOM_DD':>10} {'%_long':>9}")
    print("-" * 72)

    results = []
    for t in TICKERS:
        prices_t = prices_all[[t]]
        # Buy-and-hold reference per asset
        bh = buy_and_hold(prices_t, t)
        bh_sharpe = sharpe_ann(bh.pct_change())
        # TSMOM solo (per-asset signal, no overlay, no TC for pure signal evaluation)
        alloc = PortfolioAllocator([t])
        eq, m, hist = run_backtest(
            prices_t, alloc, method="tsmom",
            rebalance_freq_days=21, warmup_days=252,
            transaction_cost_bps=10.0,
            tsmom_lookback_days=252,
        )
        n_long = sum(1 for h in hist if h.weights.get(t, 0) > 0)
        pct_long = n_long / len(hist) * 100 if hist else 0
        tsmom_sharpe = m.sharpe_daily_annualized
        results.append((t, bh_sharpe, tsmom_sharpe, m.cagr, m.max_drawdown, pct_long))
        print(f"{t:<8} {bh_sharpe:>10.2f} {tsmom_sharpe:>14.2f} "
              f"{m.cagr*100:>11.2f}% {m.max_drawdown*100:>9.1f}% {pct_long:>8.1f}%")

    print()
    # Gate evaluation
    sharpes = [r[2] for r in results]
    n_pass_05 = sum(1 for s in sharpes if s > 0.5)
    n_pass_04 = sum(1 for s in sharpes if s > 0.4)
    print("=== Per-asset gate evaluation (plan J3) ===")
    print(f"  ≥3/4 actifs Sharpe > 0.5 (PASS bar) : {'PASS' if n_pass_05 >= 3 else 'FAIL'} ({n_pass_05}/4)")
    print(f"  ≥2/4 actifs Sharpe > 0.4 (kill rule) : {'OK' if n_pass_04 >= 2 else 'KILL'} ({n_pass_04}/4)")
    print()

    # Diagnostic : Sharpe TSMOM vs BH per asset (added value of signal)
    print("Per-asset added value (TSMOM Sharpe - BH Sharpe) :")
    for t, bh, tsmom, _, _, _ in results:
        delta = tsmom - bh
        verdict = "TSMOM > BH" if delta > 0 else "BH > TSMOM"
        print(f"  {t:<5} : Δ = {delta:+.2f} — {verdict}")


if __name__ == "__main__":
    main()
