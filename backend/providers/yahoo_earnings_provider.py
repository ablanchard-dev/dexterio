"""Yahoo earnings provider — S+2 P0.

Fetches earnings dates + EPS surprise per ticker.

Strategy :
  - Primary : yfinance.Ticker(...).earnings_dates per-ticker (~25 quarters
    history, ~6.25 years). Slower (1 call per ticker) but deeper history.
  - Fallback batch : yahooquery.Ticker(...).earning_history (4 quarters
    only, but 1 batch call for 100+ symbols). Used for quick recent data.

Returns long format DataFrame :
    columns : symbol, earnings_date, eps_estimate, eps_actual,
              surprise_pct, source

Kill behavior per plan : if Yahoo earnings fragile (rate limit, garbage data,
broken endpoint), report immediately. Pas de bricolage avec 15 fallbacks.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import yfinance as yf

from providers import Provider

logger = logging.getLogger(__name__)


class YahooEarningsProvider(Provider):
    """Yahoo earnings (date + EPS surprise) provider.

    Primary : yfinance per-ticker (deep history ~25Q).
    Fallback : yahooquery batch (shallow history 4Q but fast).
    """

    name = "yahoo_earnings"

    def __init__(self, use_batch_fallback: bool = False,
                 per_ticker_sleep: float = 0.1,
                 max_retries: int = 2):
        """Init provider.

        Args:
            use_batch_fallback : if True, use yahooquery batch (only 4Q history)
            per_ticker_sleep : seconds to sleep between yfinance per-ticker calls
            max_retries : max retries on per-ticker failure
        """
        self.use_batch_fallback = use_batch_fallback
        self.per_ticker_sleep = per_ticker_sleep
        self.max_retries = max_retries

    def fetch(self, symbols: list[str], start: str, end: str,
              **kwargs: Any) -> pd.DataFrame:
        """Fetch earnings per symbol within date range.

        Args:
            symbols : list of tickers
            start : YYYY-MM-DD inclusive earnings_date filter
            end : YYYY-MM-DD inclusive earnings_date filter
            **kwargs : ignored (provider has its own state)

        Returns:
            DataFrame long format: symbol, earnings_date, eps_estimate,
                                    eps_actual, surprise_pct, source
        """
        if not symbols:
            return pd.DataFrame()

        if self.use_batch_fallback:
            df = self._fetch_batch(symbols)
        else:
            df = self._fetch_per_ticker(symbols)

        if df.empty:
            return df

        # Filter by date range
        df["earnings_date"] = pd.to_datetime(df["earnings_date"]).dt.tz_localize(None)
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        df = df[(df["earnings_date"] >= start_dt) & (df["earnings_date"] <= end_dt)]
        return df.sort_values(["symbol", "earnings_date"]).reset_index(drop=True)

    def _fetch_per_ticker(self, symbols: list[str]) -> pd.DataFrame:
        """Per-ticker fetch via yfinance (deep history)."""
        records = []
        failed_tickers = []
        for i, sym in enumerate(symbols):
            success = False
            for attempt in range(self.max_retries + 1):
                try:
                    t = yf.Ticker(sym)
                    ed = t.earnings_dates
                    if ed is None or ed.empty:
                        logger.warning(f"{sym}: no earnings data (attempt {attempt+1})")
                        break
                    sub = ed.reset_index()
                    sub.columns = [c.lower().replace(" ", "_").replace("(%)", "_pct")
                                   for c in sub.columns]
                    # Standardize column names
                    sub = sub.rename(columns={
                        "earnings_date": "earnings_date",
                        "eps_estimate": "eps_estimate",
                        "reported_eps": "eps_actual",
                        "surprise_pct": "surprise_pct",
                    })
                    sub["symbol"] = sym
                    sub["source"] = "yfinance_per_ticker"
                    records.append(sub)
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"{sym}: attempt {attempt+1} failed: {e}")
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (attempt + 1))
            if not success:
                failed_tickers.append(sym)
            time.sleep(self.per_ticker_sleep)
            if (i + 1) % 50 == 0:
                logger.info(f"yahoo_earnings progress: {i+1}/{len(symbols)} "
                             f"({len(failed_tickers)} failed)")

        if failed_tickers:
            logger.warning(f"yahoo_earnings: {len(failed_tickers)} symbols failed: "
                            f"{failed_tickers[:10]}{'...' if len(failed_tickers)>10 else ''}")

        if not records:
            return pd.DataFrame()

        df = pd.concat(records, ignore_index=True)
        # Ensure standard columns
        for col in ["symbol", "earnings_date", "eps_estimate", "eps_actual",
                    "surprise_pct", "source"]:
            if col not in df.columns:
                df[col] = pd.NA
        return df[["symbol", "earnings_date", "eps_estimate", "eps_actual",
                   "surprise_pct", "source"]]

    def _fetch_batch(self, symbols: list[str]) -> pd.DataFrame:
        """Batch fetch via yahooquery (4Q history only, fast)."""
        try:
            from yahooquery import Ticker
        except ImportError:
            logger.error("yahooquery not installed — cannot use batch fallback")
            return pd.DataFrame()

        t = Ticker(symbols)
        eh = t.earning_history
        if not isinstance(eh, pd.DataFrame) or eh.empty:
            logger.warning("yahooquery earning_history returned empty/non-DF")
            return pd.DataFrame()

        eh = eh.reset_index()
        # yahooquery columns : symbol, row, maxAge, epsActual, epsEstimate,
        # epsDifference, surprisePercent, quarter, currency, period
        eh = eh.rename(columns={
            "symbol": "symbol",
            "quarter": "earnings_date",
            "epsEstimate": "eps_estimate",
            "epsActual": "eps_actual",
            "surprisePercent": "surprise_pct",
        })
        eh["source"] = "yahooquery_batch"
        return eh[["symbol", "earnings_date", "eps_estimate", "eps_actual",
                   "surprise_pct", "source"]]
