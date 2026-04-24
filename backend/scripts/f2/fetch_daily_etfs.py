"""F2 Portfolio-first — fetch daily ETF universe via yfinance.

Univers : SPY, QQQ, IWM, DIA, EFA, EEM (6 ETFs couvrant US large/small/intl
développé + emergent). Data daily OHLCV adj-close, 2023-01-01 → today.
Stockée parquet dans backend/data/f2_daily/<ticker>_1d.parquet.

Usage :
    python backend/scripts/f2/fetch_daily_etfs.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

TICKERS = [
    "SPY", "QQQ", "IWM", "DIA", "EFA", "EEM",  # v1 initial univers (equities)
    "GLD", "TLT", "FXI",                        # v2 extension : gold, bonds, china
    "^VIX",                                      # v2 regime overlay
]
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "f2_daily"
START = "2019-06-01"  # v3 extend : capture COVID shock (Mar 2020) + 2022 bear
END = "2025-11-30"


def fetch_and_save(ticker: str) -> int:
    df = yf.download(ticker, start=START, end=END, interval="1d",
                     progress=False, auto_adjust=False)
    if df.empty:
        print(f"{ticker}: no data")
        return 0
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "date"
    df = df.reset_index()
    df["ticker"] = ticker
    # ^VIX → VIX filename (no caret on disk)
    safe_name = ticker.replace("^", "")
    path = OUT_DIR / f"{safe_name}_1d.parquet"
    df.to_parquet(path, index=False)
    print(f"{ticker}: {len(df)} bars → {path}")
    return len(df)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for t in TICKERS:
        fetch_and_save(t)


if __name__ == "__main__":
    main()
