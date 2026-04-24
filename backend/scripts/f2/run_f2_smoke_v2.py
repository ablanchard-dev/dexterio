"""F2 v2 smoke — extended univers (9 ETFs) + VIX regime overlay + slippage +
cross-regime split + 2022-2023 drawdown stress.

Univers v2 : SPY, QQQ, IWM, DIA, EFA, EEM (v1) + GLD, TLT, FXI (v2 extension).
Overlays : vol_target + vix_regime (fertile 15-25, panic >30, low-vol <13).
Transaction costs : 10 bps per turnover (realistic ETF spread + commission).

Reports Sharpe, Martin, max DD, CAGR, vol + cross-regime split (low/fertile/panic VIX).

Usage : python backend/scripts/f2/run_f2_smoke_v2.py
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
TICKERS_V1 = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"]
TICKERS_V2 = TICKERS_V1 + ["GLD", "TLT", "FXI"]


def load_prices(tickers):
    frames = []
    for t in tickers:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def load_vix():
    df = pd.read_parquet(DATA_DIR / "VIX_1d.parquet")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")["Close"]
    df.name = "VIX"
    return df


def regime_split_metrics(equity: pd.Series, vix: pd.Series) -> dict:
    """Split equity returns by VIX regime."""
    aligned_idx = equity.index.intersection(vix.index)
    eq = equity.loc[aligned_idx]
    vx = vix.loc[aligned_idx]
    returns = eq.pct_change().dropna()
    vx_at_ret = vx.shift(1).reindex(returns.index)

    splits = {
        "low_vol (VIX<15)": (vx_at_ret < 15),
        "fertile (15-25)": ((vx_at_ret >= 15) & (vx_at_ret < 25)),
        "elevated (25-30)": ((vx_at_ret >= 25) & (vx_at_ret < 30)),
        "panic (>=30)": (vx_at_ret >= 30),
    }
    out = {}
    for name, mask in splits.items():
        r = returns[mask]
        if len(r) < 5:
            out[name] = {"n": len(r), "mean": 0, "sharpe": 0}
            continue
        sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
        out[name] = {"n": int(len(r)), "mean_daily": float(r.mean()),
                     "sharpe_ann": float(sharpe), "total_contrib": float(r.sum())}
    return out


def run_strategy(prices, alloc, method, overlays, label, vix_series=None, tc_bps=0):
    try:
        eq, m, _ = run_backtest(
            prices, alloc, method=method, overlays=overlays,
            rebalance_freq_days=21, warmup_days=252,
            transaction_cost_bps=tc_bps,
            vix_series=vix_series,
        )
        return {
            "label": label,
            "return": m.total_return * 100,
            "cagr": m.cagr * 100,
            "sharpe": m.sharpe_daily_annualized,
            "martin": m.martin_ratio,
            "max_dd": m.max_drawdown * 100,
            "vol": m.volatility_annualized * 100,
            "cash_avg": m.cash_avg * 100,
            "n_days": m.n_days,
            "equity": eq,
        }
    except Exception as e:
        return {"label": label, "error": str(e)}


def main() -> None:
    prices = load_prices(TICKERS_V2)
    vix = load_vix()
    print(f"Corpus : {prices.index[0].date()} → {prices.index[-1].date()} ({len(prices)} days, {len(TICKERS_V2)} tickers)")
    print(f"VIX : {vix.index[0].date()} → {vix.index[-1].date()} (n={len(vix)})")
    print()

    bh = buy_and_hold(prices, "SPY")
    print(f"SPY buy-and-hold : return={(bh.iloc[-1]/bh.iloc[0]-1)*100:.1f}%, "
          f"Sharpe={bh.pct_change().dropna().mean()/bh.pct_change().dropna().std()*np.sqrt(252):.2f}")
    print()

    alloc_v1 = PortfolioAllocator(TICKERS_V1)
    alloc_v2 = PortfolioAllocator(TICKERS_V2)

    configs = [
        ("equal_weight_v1 (6 ETFs)",           alloc_v1, "equal_weight", None, 0),
        ("equal_weight_v2 (9 ETFs)",           alloc_v2, "equal_weight", None, 0),
        ("equal_weight_v2 + tc10bps",          alloc_v2, "equal_weight", None, 10),
        ("risk_parity_v2",                     alloc_v2, "risk_parity", None, 10),
        ("risk_parity_v2 + VIX_overlay",       alloc_v2, "risk_parity", ["vix_regime"], 10),
        ("momentum_v2 J&T top3",               alloc_v2, "momentum", None, 10),
        ("momentum_v2 + VIX_overlay",          alloc_v2, "momentum", ["vix_regime"], 10),
        ("momentum_v2 + vol_tgt + VIX",        alloc_v2, "momentum", ["vol_target", "vix_regime"], 10),
    ]

    print(f"{'strategy':<40} {'ret':>6} {'CAGR':>6} {'Sharpe':>7} {'Martin':>7} {'maxDD':>7} {'vol':>6} {'cash':>6}")
    print("-" * 105)
    results = []
    for label, alloc, method, overlays, tc in configs:
        r = run_strategy(prices, alloc, method, overlays, label, vix_series=vix, tc_bps=tc)
        if "error" in r:
            print(f"{label:<40} FAIL : {r['error']}")
            continue
        results.append(r)
        print(f"{label:<40} {r['return']:>5.1f}% {r['cagr']:>5.2f}% {r['sharpe']:>7.2f} {r['martin']:>7.2f} {r['max_dd']:>6.1f}% {r['vol']:>5.1f}% {r['cash_avg']:>5.1f}%")

    # Cross-regime split for best strategy (risk_parity + VIX)
    print()
    print("=== Cross-regime split : risk_parity_v2 + VIX_overlay ===")
    best = next((r for r in results if r["label"] == "risk_parity_v2 + VIX_overlay"), None)
    if best:
        rs = regime_split_metrics(best["equity"], vix)
        for regime, stats in rs.items():
            if stats["n"] < 5:
                print(f"  {regime:<20} n={stats['n']:>3} (insufficient)")
                continue
            print(f"  {regime:<20} n={stats['n']:>3}  mean_daily={stats['mean_daily']*100:>6.3f}%  "
                  f"Sharpe_ann={stats['sharpe_ann']:>5.2f}  total_contrib={stats['total_contrib']*100:>6.2f}%")

    # 2022-2023 drawdown stress : identify the worst 60-day window
    print()
    print("=== Worst 60-day drawdown analysis ===")
    for r in results[:3]:
        eq = r["equity"]
        rolling_min = eq / eq.expanding().max() - 1
        worst_dd = rolling_min.min()
        worst_date = rolling_min.idxmin()
        print(f"  {r['label']:<40} worst DD {worst_dd*100:>6.1f}% on {worst_date.date()}")


if __name__ == "__main__":
    main()
