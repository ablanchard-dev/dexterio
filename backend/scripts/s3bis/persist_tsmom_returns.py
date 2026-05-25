"""S+3-bis pre-T1 : re-run TSMOM 4 ETFs et persist daily returns.

Re-run technique pour obtenir l'artefact equity curve manquant du plan v4.0
TSMOM verdict (verdict G4 documenté mais .parquet returns daily non persisté).
PAS une nouvelle variante — paramètres frozen identiques verdict v4.0.

Output : data/equities/tsmom_4etf_daily_returns.parquet
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
from engines.portfolio.backtester import run_backtest

DATA_DIR = backend_dir / "data" / "f2_daily"
TICKERS = ["SPY", "QQQ", "GLD", "TLT"]


def load_prices(tickers: list[str]) -> pd.DataFrame:
    frames = []
    for t in tickers:
        df = pd.read_parquet(DATA_DIR / f"{t}_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")[["Close"]].rename(columns={"Close": t})
        frames.append(df)
    return pd.concat(frames, axis=1).sort_index().ffill().dropna()


def main() -> None:
    prices = load_prices(TICKERS)
    print(f"Loaded {len(prices)} days × 4 ETFs (SPY/QQQ/GLD/TLT)")

    alloc = PortfolioAllocator(TICKERS)

    # TSMOM with vol target 10% (matches plan v4.0 verdict spec)
    eq, m, _ = run_backtest(
        prices, alloc, method="tsmom",
        overlays=["vol_target"],
        rebalance_freq_days=21,
        warmup_days=252,  # 12-month lookback
        transaction_cost_bps=10.0,
        target_annual_vol=0.10,
        tsmom_lookback_days=252,
    )
    rets = eq.pct_change().fillna(0)
    print(f"TSMOM 6.5y : Sharpe={m.sharpe_daily_annualized:.3f}, "
          f"CAGR={m.cagr*100:.2f}%, max_DD={m.max_drawdown*100:.2f}%")
    print(f"  vol target 10%, n_rebalances={m.n_rebalances}")

    # Persist
    out_path = backend_dir / "data" / "equities" / "tsmom_4etf_daily_returns.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"equity": eq, "ret": rets})
    df.to_parquet(out_path)
    print(f"Saved daily returns → {out_path}")


if __name__ == "__main__":
    main()
