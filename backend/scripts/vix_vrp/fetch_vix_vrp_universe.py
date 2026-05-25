"""S+1 Plan VIX VRP — fetch VXX/SVXY/UVXY ETF proxies via yfinance free.

Stratégie : volatility risk premium (VRP) = sellers of vol earn structural
premium because implied vol > realized vol on average. Sans options chain,
proxy via VIX futures ETFs :

  - VXX : long VIX futures (decays in contango, gains in backwardation)
  - SVXY : -0.5x VIX (gains in contango, loses in backwardation, post-2018-feb
    leverage cut from -1x after XIV blowup)
  - UVXY : +1.5x VIX (leveraged long, post-2018 cut from 2x)

Note : current series leverage (SVXY -0.5x, UVXY 1.5x) post-2018-02 reset.
yfinance retourne la série courante. 6.5y (2019-06-01 → 2025-11-30) couvre
toutes leverages courantes + COVID March 2020 + 2022 bear.

VIX (^VIX) déjà disponible dans data/f2_daily/VIX_1d.parquet.

Usage : python backend/scripts/vix_vrp/fetch_vix_vrp_universe.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "vix_vrp"
TICKERS = ["VXX", "SVXY", "UVXY"]
START = "2019-06-01"
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
    path = OUT_DIR / f"{ticker}_1d.parquet"
    df.to_parquet(path, index=False)
    print(f"{ticker}: {len(df)} bars → {path}")
    return len(df)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for t in TICKERS:
        fetch_and_save(t)


if __name__ == "__main__":
    main()
