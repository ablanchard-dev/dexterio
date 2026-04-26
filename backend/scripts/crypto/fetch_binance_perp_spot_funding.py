"""Fetch Binance BTC/ETH perp + spot daily klines + funding rate history (2y).

Plan v4.0 J6 Priorité #2 — Crypto basis/funding harvest skeleton.
Public API endpoints, no auth required.

Fetches :
  - Spot daily klines (api.binance.com/api/v3/klines)
  - Perp futures daily klines (fapi.binance.com/fapi/v1/klines)
  - Funding rate history every 8h (fapi.binance.com/fapi/v1/fundingRate)

Outputs :
  - data/crypto/<SYMBOL>_spot_1d.parquet
  - data/crypto/<SYMBOL>_perp_1d.parquet
  - data/crypto/<SYMBOL>_funding_8h.parquet

Usage : python backend/scripts/crypto/fetch_binance_perp_spot_funding.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "crypto"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

END_MS = int(datetime(2026, 4, 25, tzinfo=timezone.utc).timestamp() * 1000)
START_MS = int(datetime(2024, 4, 25, tzinfo=timezone.utc).timestamp() * 1000)

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fetch(url: str, retries: int = 3, sleep: float = 0.5) -> list:
    """Fetch JSON from URL with simple retry."""
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            r = urllib.request.urlopen(req, timeout=20)
            return json.loads(r.read())
        except Exception as e:
            last_err = e
            time.sleep(sleep * (i + 1))
    raise RuntimeError(f"Fetch failed after {retries} retries: {last_err}")


def fetch_klines(symbol: str, interval: str, base: str, start_ms: int,
                 end_ms: int) -> pd.DataFrame:
    """Fetch klines (paginated). base = 'api.binance.com/api/v3' (spot) or
    'fapi.binance.com/fapi/v1' (perp futures)."""
    all_rows = []
    cur = start_ms
    while cur < end_ms:
        url = (f"https://{base}/klines?symbol={symbol}&interval={interval}"
               f"&startTime={cur}&endTime={end_ms}&limit=1000")
        data = _fetch(url)
        if not data:
            break
        all_rows.extend(data)
        last_ts = data[-1][0]
        if len(data) < 1000:
            break
        # Advance past last bar
        cur = last_ts + 1
        time.sleep(0.1)  # rate-limit politeness
    cols = ["open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"]
    df = pd.DataFrame(all_rows, columns=cols)
    df["datetime"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume", "quote_vol"]:
        df[c] = df[c].astype(float)
    df = df[["datetime", "open", "high", "low", "close", "volume", "quote_vol"]]
    return df.set_index("datetime").sort_index()


def fetch_funding(symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """Fetch funding rate history (every 8h, perp only). Paginated by limit=1000."""
    all_rows = []
    cur = start_ms
    while cur < end_ms:
        url = (f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}"
               f"&startTime={cur}&endTime={end_ms}&limit=1000")
        data = _fetch(url)
        if not data:
            break
        all_rows.extend(data)
        last_ts = data[-1]["fundingTime"]
        if len(data) < 1000:
            break
        cur = last_ts + 1
        time.sleep(0.1)
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df["markPrice"] = df["markPrice"].astype(float)
    return df.set_index("datetime").sort_index()[["symbol", "fundingRate", "markPrice"]]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sym in SYMBOLS:
        print(f"\n=== {sym} ===")
        # Spot daily
        print(f"  Fetching spot 1d ({datetime.fromtimestamp(START_MS/1000)} → "
              f"{datetime.fromtimestamp(END_MS/1000)})...")
        spot = fetch_klines(sym, "1d", "api.binance.com/api/v3",
                             START_MS, END_MS)
        path_spot = OUT_DIR / f"{sym}_spot_1d.parquet"
        spot.reset_index().to_parquet(path_spot, index=False)
        print(f"  spot {len(spot)} bars → {path_spot.name}")

        # Perp daily
        print(f"  Fetching perp 1d...")
        perp = fetch_klines(sym, "1d", "fapi.binance.com/fapi/v1",
                             START_MS, END_MS)
        path_perp = OUT_DIR / f"{sym}_perp_1d.parquet"
        perp.reset_index().to_parquet(path_perp, index=False)
        print(f"  perp {len(perp)} bars → {path_perp.name}")

        # Funding rate
        print(f"  Fetching funding rate 8h...")
        funding = fetch_funding(sym, START_MS, END_MS)
        if funding.empty:
            print(f"  funding EMPTY")
        else:
            path_funding = OUT_DIR / f"{sym}_funding_8h.parquet"
            funding.reset_index().to_parquet(path_funding, index=False)
            avg_fr = funding["fundingRate"].mean()
            apr_avg = avg_fr * 3 * 365 * 100  # 3 fundings/day
            pos_pct = (funding["fundingRate"] > 0).mean() * 100
            print(f"  funding {len(funding)} entries → {path_funding.name}")
            print(f"  avg funding rate: {avg_fr*100:.5f}% per 8h "
                  f"(annualized ~{apr_avg:.2f}% APR if persistent)")
            print(f"  % windows positive funding: {pos_pct:.1f}%")


if __name__ == "__main__":
    main()
