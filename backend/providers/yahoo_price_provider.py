"""Yahoo Finance price provider via yfinance — S+2 P0.

Wrapper léger autour yfinance.download pour OHLCV daily multi-ticker.
Renvoie DataFrame long-format normalisé : columns [symbol, date, open, high,
low, close, adj_close, volume].

Usage :
    from providers.yahoo_price_provider import YahooPriceProvider
    p = YahooPriceProvider()
    df = p.fetch(['AAPL', 'MSFT'], '2019-06-01', '2025-11-30')
    p.save(df, Path('data/equities/sample_prices.parquet'),
           symbols=['AAPL', 'MSFT'], start='2019-06-01', end='2025-11-30')
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

from providers import Provider

logger = logging.getLogger(__name__)


class YahooPriceProvider(Provider):
    """Yahoo Finance OHLCV daily price provider via yfinance.

    Notes :
      - Free, no API key required
      - Rate limited (~2000 req/hour reportedly)
      - Auto-batches via yfinance.download multi-ticker
      - Returns long format (one row per symbol-date)
    """

    name = "yahoo_price"

    def fetch(self, symbols: list[str], start: str, end: str,
              **kwargs: Any) -> pd.DataFrame:
        """Fetch OHLCV daily for symbols.

        Args:
            symbols : list of tickers (e.g. ['AAPL', 'MSFT'])
            start : YYYY-MM-DD inclusive
            end : YYYY-MM-DD inclusive
            **kwargs : passed to yfinance.download (interval, auto_adjust, etc.)

        Returns:
            DataFrame long format columns : symbol, date, open, high, low,
                                             close, adj_close, volume
        """
        interval = kwargs.pop("interval", "1d")
        auto_adjust = kwargs.pop("auto_adjust", False)

        if not symbols:
            return pd.DataFrame()

        # yfinance.download supports list directly with group_by='ticker'
        raw = yf.download(
            tickers=symbols,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=auto_adjust,
            group_by="ticker",
            progress=False,
            threads=True,
            **kwargs,
        )

        if raw.empty:
            logger.warning(f"No data returned for symbols={symbols}")
            return pd.DataFrame()

        # Normalize : if multi-ticker, MultiIndex columns (ticker, OHLCV); single = flat
        records = []
        if isinstance(raw.columns, pd.MultiIndex):
            for sym in symbols:
                if sym not in raw.columns.get_level_values(0):
                    logger.warning(f"Symbol {sym} returned no data, skipping")
                    continue
                sub = raw[sym].copy()
                sub = sub.reset_index()
                sub["symbol"] = sym
                records.append(sub)
            if not records:
                return pd.DataFrame()
            df = pd.concat(records, ignore_index=True)
        else:
            # Single ticker case (or fallback)
            df = raw.reset_index()
            df["symbol"] = symbols[0] if symbols else "UNKNOWN"

        # Standardize columns
        df.columns = [c.lower().replace(" ", "_") if isinstance(c, str) else c
                      for c in df.columns]
        # Rename common aliases
        rename_map = {
            "date": "date",
            "datetime": "date",
            "adj_close": "adj_close",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Ensure required columns exist (fill NaN if missing)
        required = ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]
        for col in required:
            if col not in df.columns:
                df[col] = pd.NA

        # Drop rows with all-NaN OHLCV (yfinance sometimes returns padding)
        df = df.dropna(subset=["close"], how="all")
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

        return df[required].sort_values(["symbol", "date"]).reset_index(drop=True)
