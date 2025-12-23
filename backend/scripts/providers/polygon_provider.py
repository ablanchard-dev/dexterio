"""Polygon.io provider for 1-minute OHLCV aggregates.

Contract:
- Input: symbol, start_date (inclusive), end_date (exclusive)
- Output DataFrame columns: datetime (tz-aware UTC), open, high, low, close, volume
- Handles pagination via `next_url`.

API endpoint used:
- GET /v2/aggs/ticker/{ticker}/range/1/minute/{from}/{to}
  params: adjusted=true, sort=asc, limit=50000, apiKey=...

Notes:
- Polygon's {from}/{to} are treated as dates and are effectively inclusive.
  To respect our [start, end) contract, we request to=(end-1day).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests


@dataclass
class PolygonConfig:
    api_key: str
    adjusted: bool = True
    sort: str = "asc"
    limit: int = 50000
    per_page_delay_seconds: float = 0.0


def _to_inclusive_to_date(end_exclusive: date) -> Optional[date]:
    to_date = end_exclusive - timedelta(days=1)
    return to_date


def _build_first_url(symbol: str, start_inclusive: date, end_exclusive: date) -> Optional[str]:
    to_date = _to_inclusive_to_date(end_exclusive)
    if to_date < start_inclusive:
        return None
    return f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{start_inclusive.isoformat()}/{to_date.isoformat()}"


def _fetch_page(session: requests.Session, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    resp = session.get(url, params=params, timeout=60)
    if resp.status_code == 429:
        # Let caller retry/backoff
        raise RuntimeError("polygon_rate_limited_429")
    if resp.status_code >= 400:
        raise RuntimeError(f"polygon_http_{resp.status_code}: {resp.text[:200]}")
    return resp.json()


def download_1m_aggregates(
    *,
    session: requests.Session,
    symbol: str,
    start: date,
    end: date,
    cfg: PolygonConfig,
) -> pd.DataFrame:
    """Download aggregates and return a normalized DataFrame."""

    first_url = _build_first_url(symbol, start, end)
    if not first_url:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

    url: Optional[str] = first_url
    all_rows: List[Dict[str, Any]] = []

    # First request uses standard params. Follow-up requests use `next_url`.
    first_params: Dict[str, Any] = {
        "adjusted": "true" if cfg.adjusted else "false",
        "sort": cfg.sort,
        "limit": cfg.limit,
        "apiKey": cfg.api_key,
    }

    while url:
        # Polygon requires apiKey even on next_url calls.
        params = first_params if url == first_url else {"apiKey": cfg.api_key}
        payload = _fetch_page(session, url, params=params)

        results = payload.get("results") or []
        for r in results:
            # t: unix ms timestamp
            ts_ms = r.get("t")
            if ts_ms is None:
                continue
            dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            all_rows.append(
                {
                    "datetime": dt,
                    "open": r.get("o"),
                    "high": r.get("h"),
                    "low": r.get("l"),
                    "close": r.get("c"),
                    "volume": r.get("v"),
                }
            )

        url = payload.get("next_url")
        if url and cfg.per_page_delay_seconds:
            import time

            time.sleep(cfg.per_page_delay_seconds)

    if not all_rows:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)

    # Ensure correct ordering and types
    df = df.sort_values("datetime").reset_index(drop=True)

    return df
