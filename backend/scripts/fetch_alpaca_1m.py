"""
Fetch 1m OHLCV bars from Alpaca (free tier, IEX feed).

Usage:
    python scripts/fetch_alpaca_1m.py --symbols SPY QQQ --start 2024-06-01 --end 2025-11-30

Output:
    data/market/{symbol}_1m.parquet   (one file per symbol, append-safe)

The script fetches day-by-day (weekdays only), respects Alpaca's 10k bar page
limit, and resumes from the last bar already in the parquet file.
"""
import argparse
import os
import sys
import time
import logging
from datetime import datetime, timedelta, date, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "market"
BARS_PER_PAGE = 10_000  # Alpaca max


def _headers():
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        sys.exit("ALPACA_API_KEY / ALPACA_API_SECRET missing from .env")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def fetch_bars(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch all 1m bars for symbol between start and end (ISO dates)."""
    headers = _headers()
    all_bars = []
    next_token = None
    page = 0

    while True:
        params = {
            "timeframe": "1Min",
            "start": f"{start}T00:00:00Z",
            "end": f"{end}T23:59:59Z",
            "limit": BARS_PER_PAGE,
            "feed": "iex",
            "adjustment": "split",
        }
        if next_token:
            params["page_token"] = next_token

        r = requests.get(f"{ALPACA_DATA_URL}/{symbol}/bars",
                         headers=headers, params=params, timeout=30)

        if r.status_code == 429:
            logger.warning("Rate limited, sleeping 60s...")
            time.sleep(60)
            continue

        if r.status_code != 200:
            logger.error(f"Alpaca error {r.status_code}: {r.text[:300]}")
            break

        data = r.json()
        bars = data.get("bars") or []
        all_bars.extend(bars)
        page += 1

        next_token = data.get("next_page_token")
        if not next_token or not bars:
            break

        # Be polite — small delay between pages
        time.sleep(0.2)

    if not all_bars:
        return pd.DataFrame()

    df = pd.DataFrame(all_bars)
    # Rename Alpaca columns → our standard
    df = df.rename(columns={
        "t": "datetime",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
        "vw": "vwap",
        "n": "trades",
    })
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["symbol"] = symbol
    df = df.sort_values("datetime").reset_index(drop=True)

    logger.info(f"  {symbol}: fetched {len(df)} bars ({page} pages), "
                f"{df['datetime'].min()} → {df['datetime'].max()}")
    return df


def load_existing(symbol: str) -> pd.DataFrame:
    """Load existing parquet if present."""
    path = OUTPUT_DIR / f"{symbol}_1m.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        return df
    return pd.DataFrame()


def save(symbol: str, df: pd.DataFrame):
    """Save to parquet (overwrite with merged data)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{symbol}_1m.parquet"
    df = df.sort_values("datetime").reset_index(drop=True)
    # Dedup
    df = df.drop_duplicates(subset=["datetime"], keep="first")
    df.to_parquet(path, index=False)
    logger.info(f"  Saved {len(df)} bars → {path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch 1m OHLCV from Alpaca")
    parser.add_argument("--symbols", nargs="+", default=["SPY", "QQQ"])
    parser.add_argument("--start", default="2024-06-01",
                        help="Start date YYYY-MM-DD (default: 2024-06-01)")
    parser.add_argument("--end", default=None,
                        help="End date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()

    if args.end is None:
        args.end = (date.today() - timedelta(days=1)).isoformat()

    logger.info(f"Fetching {args.symbols} from {args.start} to {args.end}")

    for symbol in args.symbols:
        logger.info(f"\n{'='*40} {symbol} {'='*40}")

        existing = load_existing(symbol)
        if not existing.empty:
            last_dt = existing["datetime"].max()
            resume_date = (last_dt.date() + timedelta(days=1)).isoformat()
            if resume_date > args.end:
                logger.info(f"  {symbol}: already up to date ({last_dt})")
                continue
            logger.info(f"  Resuming from {resume_date} (have {len(existing)} bars)")
            start = resume_date
        else:
            start = args.start

        new_bars = fetch_bars(symbol, start, args.end)

        if new_bars.empty:
            logger.info(f"  {symbol}: no new bars")
            if not existing.empty:
                save(symbol, existing)
            continue

        # Merge with existing
        if not existing.empty:
            combined = pd.concat([existing, new_bars], ignore_index=True)
        else:
            combined = new_bars

        save(symbol, combined)

    logger.info("\nDone!")


if __name__ == "__main__":
    main()
