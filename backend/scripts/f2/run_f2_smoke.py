"""F2 Portfolio smoke test — multi-asset daily allocation backtest.

Loads 6-ETF daily corpus, runs PortfolioAllocator with various methods, and
compares against SPY buy-and-hold. Goal : validate F2 infrastructure + obtain
baseline metrics (Sharpe, Martin, max DD) for comparison with ICT intraday
bots (all ICT had ~0 Sharpe).

Usage : python backend/scripts/f2/run_f2_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.portfolio.allocator import PortfolioAllocator
from engines.portfolio.backtester import buy_and_hold, run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"]


def load_prices() -> pd.DataFrame:
    """Load daily close prices into a single date-indexed DataFrame."""
    frames = []
    for t in TICKERS:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    prices = pd.concat(frames, axis=1).sort_index()
    prices = prices.ffill().dropna()
    return prices


def main() -> None:
    prices = load_prices()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} ({len(prices)} days, {len(TICKERS)} tickers)")
    print()

    alloc = PortfolioAllocator(tickers=TICKERS)

    # Baseline 1 : buy-and-hold SPY
    bh = buy_and_hold(prices, "SPY")
    bh_metrics = {
        "total_return": f"{(bh.iloc[-1] / bh.iloc[0] - 1) * 100:.1f}%",
        "sharpe": f"{(bh.pct_change().dropna().mean() / bh.pct_change().dropna().std() * (252 ** 0.5)):.2f}",
    }
    print(f"SPY buy-and-hold : total_ret={bh_metrics['total_return']}, Sharpe={bh_metrics['sharpe']}")
    print()

    strategies = [
        ("equal_weight", {}),
        ("momentum", {"jt_lookback": 12, "jt_skip": 1, "jt_top_n": 3}),
        ("momentum_vol_target", {"method": "momentum", "overlays": ["vol_target"],
                                   "jt_lookback": 12, "jt_skip": 1, "jt_top_n": 3,
                                   "target_annual_vol": 0.12}),
        ("risk_parity", {"method": "risk_parity"}),
        ("vol_target_eq", {"method": "vol_target", "target_annual_vol": 0.12}),
    ]

    print(f"{'strategy':<22} {'return':>8} {'CAGR':>8} {'Sharpe':>7} {'Martin':>7} {'maxDD':>8} {'vol':>7} {'cash_avg':>9}")
    print("-" * 85)
    for name, kw in strategies:
        method = kw.pop("method", name.split("_vol_")[0]) if "method" not in kw else kw.pop("method")
        if name == "equal_weight": method = "equal_weight"
        elif name == "momentum": method = "momentum"
        try:
            eq, m, hist = run_backtest(
                prices, alloc, method=method,
                overlays=kw.get("overlays"),
                rebalance_freq_days=21, warmup_days=252,
                **{k: v for k, v in kw.items() if k not in ("overlays", "method")},
            )
            print(f"{name:<22} {m.total_return*100:>7.1f}% {m.cagr*100:>7.2f}% {m.sharpe_daily_annualized:>7.2f} {m.martin_ratio:>7.2f} {m.max_drawdown*100:>7.1f}% {m.volatility_annualized*100:>6.1f}% {m.cash_avg*100:>8.1f}%")
        except Exception as e:
            print(f"{name:<22} FAIL : {e}")


if __name__ == "__main__":
    main()
