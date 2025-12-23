"""P0.6.3 - Windowed intraday downloader (1m) with pluggable providers.

Contract (non negotiable):
- Output Parquet per symbol:
  - /app/data/historical/1m/SPY.parquet
  - /app/data/historical/1m/QQQ.parquet
- Pipeline: download chunk(N days) → concat → sort → dedupe → normalize tz(UTC) → quality gates → write parquet
- Quality gates minimum:
  (1) timestamps timezone unique (UTC)
  (2) 0 duplicate timestamps after merge
  (3) OHLCV non-NaN on RTH (sessions computed in US/Eastern; stored timestamps in UTC)
  (4) report missing bars % per day + tag corrupted days (>5%)
- Outputs:
  - Parquet final per symbol
  - /app/data/historical/1m/data_quality_{SYMBOL}.json
  - Logs de progression par fenêtre (dates + nb lignes + retries)

Providers:
- yfinance (limited to ~30 days for 1m)
- polygon (requires env var POLYGON_API_KEY)

Date convention:
- CLI uses [start, end) where end is exclusive.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

try:
    import yfinance as yf
except Exception:
    yf = None

from scripts.quality_gates import normalize_datetime_to_utc, run_quality_gates
from scripts.providers.polygon_provider import PolygonConfig, download_1m_aggregates


logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    symbol: str
    start: date
    end: date
    window_days: int
    out: Path
    provider: str = "yfinance"  # yfinance | polygon

    retries: int = 4
    backoff_seconds: float = 2.0
    request_delay_seconds: float = 1.0

    # Polygon-specific throttling (optional)
    polygon_per_page_delay_seconds: float = 0.0
    polygon_rate_limit_sleep_seconds: float = 60.0

    max_missing_pct: float = 5.0
    debug_chunks_dir: Optional[Path] = None


def _download_window_once_yfinance(symbol: str, start: date, end: date) -> pd.DataFrame:
    if yf is None:
        raise ImportError("yfinance is not installed")

    ticker = yf.Ticker(symbol)
    df = ticker.history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1m",
    )

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]

    if "date" in df.columns and "datetime" not in df.columns:
        df = df.rename(columns={"date": "datetime"})

    if "datetime" not in df.columns:
        raise ValueError(f"yfinance returned unexpected columns: {list(df.columns)}")

    keep = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep]

    return df


def _download_window_once_polygon(
    *,
    session: requests.Session,
    symbol: str,
    start: date,
    end: date,
    per_page_delay_seconds: float,
) -> pd.DataFrame:
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY env var is required for --provider polygon")

    cfg = PolygonConfig(api_key=api_key, per_page_delay_seconds=per_page_delay_seconds)
    return download_1m_aggregates(session=session, symbol=symbol, start=start, end=end, cfg=cfg)


def download_window_with_retries(
    *,
    provider: str,
    session: Optional[requests.Session],
    symbol: str,
    start: date,
    end: date,
    retries: int,
    backoff_seconds: float,
    polygon_per_page_delay_seconds: float,
    polygon_rate_limit_sleep_seconds: float,
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    last_err: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            if provider == "yfinance":
                df = _download_window_once_yfinance(symbol, start, end)
            elif provider == "polygon":
                if session is None:
                    raise RuntimeError("polygon provider requires a requests.Session")
                df = _download_window_once_polygon(
                    session=session,
                    symbol=symbol,
                    start=start,
                    end=end,
                    per_page_delay_seconds=polygon_per_page_delay_seconds,
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")

            if df is None or df.empty:
                last_err = "empty_window"
                logger.warning("  fenêtre vide (%s → %s)", start, end)
                return None, {"attempts": attempt, "success": False, "error": last_err}

            return df, {"attempts": attempt, "success": True, "error": None}
        except Exception as e:
            last_err = repr(e)
            logger.warning("  tentative %d/%d échouée: %s", attempt, retries, last_err)

            if attempt < retries:
                # Polygon rate-limit handling: slow down aggressively.
                if "polygon_rate_limited_429" in last_err:
                    sleep_s = max(polygon_rate_limit_sleep_seconds, backoff_seconds * (2 ** (attempt - 1)))
                    logger.warning("  polygon 429 -> sleep %.1fs then retry", sleep_s)
                    time.sleep(sleep_s)
                else:
                    sleep_s = backoff_seconds * (2 ** (attempt - 1))
                    time.sleep(sleep_s)

    return None, {"attempts": retries, "success": False, "error": last_err}


def build_windows(start: date, end: date, window_days: int) -> List[Tuple[date, date]]:
    if window_days <= 0:
        raise ValueError("window_days must be > 0")

    windows: List[Tuple[date, date]] = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=window_days), end)
        windows.append((cur, nxt))
        cur = nxt
    return windows


def run(config: DownloadConfig) -> Dict[str, Any]:
    config.out.parent.mkdir(parents=True, exist_ok=True)
    if config.debug_chunks_dir is not None:
        config.debug_chunks_dir.mkdir(parents=True, exist_ok=True)

    session: Optional[requests.Session] = None
    if config.provider == "polygon":
        session = requests.Session()

    logger.info("=" * 88)
    logger.info("P0.6.3 WINDOWED DOWNLOADER | %s | provider=%s", config.symbol, config.provider)
    logger.info("Range: %s → %s | window_days=%d", config.start, config.end, config.window_days)
    logger.info("Out: %s", config.out)
    logger.info("=" * 88)

    windows = build_windows(config.start, config.end, config.window_days)
    all_chunks: List[pd.DataFrame] = []
    windows_log: List[Dict[str, Any]] = []

    for i, (w_start, w_end) in enumerate(windows, start=1):
        logger.info("[window %d/%d] %s → %s", i, len(windows), w_start, w_end)

        df, meta = download_window_with_retries(
            provider=config.provider,
            session=session,
            symbol=config.symbol,
            start=w_start,
            end=w_end,
            retries=config.retries,
            backoff_seconds=config.backoff_seconds,
            polygon_per_page_delay_seconds=config.polygon_per_page_delay_seconds,
            polygon_rate_limit_sleep_seconds=config.polygon_rate_limit_sleep_seconds,
        )

        win_info = {
            "window": i,
            "start": w_start.isoformat(),
            "end": w_end.isoformat(),
            "success": bool(meta.get("success")),
            "attempts": int(meta.get("attempts", 0)),
            "bars": int(len(df)) if df is not None else 0,
            "error": meta.get("error"),
        }
        windows_log.append(win_info)

        if df is not None and not df.empty:
            logger.info("  ok: %d bars (attempts=%d)", len(df), win_info["attempts"])
            if config.debug_chunks_dir is not None:
                chunk_path = config.debug_chunks_dir / f"{config.symbol}_chunk_{w_start}_{w_end}.parquet"
                df.to_parquet(chunk_path, index=False)
            all_chunks.append(df)
        else:
            logger.warning("  skip: no data")

        time.sleep(config.request_delay_seconds)

    if not all_chunks:
        raise RuntimeError("No data downloaded for any window")

    combined = pd.concat(all_chunks, ignore_index=True)

    # Normalize tz UTC *before* sorting/dedup to avoid mixed tz comparisons.
    combined = normalize_datetime_to_utc(combined)

    combined = combined.sort_values("datetime").reset_index(drop=True)

    before = len(combined)
    combined = combined.drop_duplicates(subset=["datetime"], keep="last").reset_index(drop=True)
    duplicates_removed = before - len(combined)

    # Final column ordering
    cols = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in combined.columns]
    combined = combined[cols]

    # Quality gates
    quality = run_quality_gates(
        combined,
        symbol=config.symbol,
        start=config.start,
        end=config.end,
        max_missing_pct=config.max_missing_pct,
    )

    quality["duplicates_removed"] = int(duplicates_removed)
    quality["windows"] = windows_log

    # Enforce downloader-level success gate (prevents silently incomplete datasets)
    successes = sum(1 for w in windows_log if w.get("success"))
    total = len(windows_log)
    success_rate = (successes / total) if total else 0.0
    gate_ok = success_rate >= 0.95
    quality.setdefault("gates", {})
    quality["gates"]["window_download_success_rate"] = {
        "passed": bool(gate_ok),
        "successes": int(successes),
        "total_windows": int(total),
        "success_rate": round(success_rate, 4),
    }
    quality["passed"] = bool(quality.get("passed", True) and gate_ok)

    # Write outputs (Parquet contract v1): DatetimeIndex (UTC) as index.
    # We keep 'datetime' for gates, but the stored parquet uses the index as source of truth.
    write_df = combined.copy()
    write_df["datetime"] = pd.to_datetime(write_df["datetime"], utc=True)
    write_df = write_df.set_index("datetime", drop=True)
    write_df.index.name = "datetime"
    write_df = write_df.sort_index()
    write_df = write_df[~write_df.index.duplicated(keep="last")]

    # Hard-fail asserts (non-negotiable)
    assert isinstance(write_df.index, pd.DatetimeIndex)
    assert write_df.index.tz is not None
    assert str(write_df.index.tz) in ("UTC", "UTC+00:00")
    assert write_df.index.is_monotonic_increasing
    assert not write_df.index.has_duplicates

    # Ensure only OHLCV columns are stored
    ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in write_df.columns]
    write_df = write_df[ohlcv_cols]

    write_df.to_parquet(config.out, index=True)

    quality_path = config.out.parent / f"data_quality_{config.symbol.upper()}.json"
    with quality_path.open("w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2)

    logger.info("\n✅ wrote parquet: %s", config.out)
    logger.info("✅ wrote quality report: %s", quality_path)
    logger.info("duplicates removed: %d", duplicates_removed)

    if not quality.get("passed", False):
        raise RuntimeError(f"Quality gates failed for {config.symbol}. See: {quality_path}")

    logger.info("quality passed: True | corrupted_days=%d", len(quality.get("corrupted_days", [])))

    return {"out": str(config.out), "quality": str(quality_path), "passed": True}


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="P0.6.3 Windowed downloader (1m)")
    parser.add_argument("--provider", type=str, default="yfinance", choices=["yfinance", "polygon"], help="Data provider")

    parser.add_argument("--symbol", required=True, type=str, help="SPY or QQQ")
    parser.add_argument("--start", required=True, type=str, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, type=str, help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--window-days", required=True, type=int, help="Window size in days (7 recommended)")
    parser.add_argument("--out", required=True, type=str, help="Output Parquet path")

    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--backoff-seconds", type=float, default=2.0)
    parser.add_argument("--request-delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-missing-pct", type=float, default=5.0)
    parser.add_argument("--debug-chunks-dir", type=str, default=None)

    # Polygon provider fine-tuning (optional)
    parser.add_argument("--polygon-per-page-delay-seconds", type=float, default=0.0)
    parser.add_argument("--polygon-rate-limit-sleep-seconds", type=float, default=60.0)

    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    symbol = args.symbol.strip().upper()

    cfg = DownloadConfig(
        symbol=symbol,
        start=_parse_date(args.start),
        end=_parse_date(args.end),
        window_days=int(args.window_days),
        out=Path(args.out),
        provider=str(args.provider),
        retries=int(args.retries),
        backoff_seconds=float(args.backoff_seconds),
        request_delay_seconds=float(args.request_delay_seconds),
        max_missing_pct=float(args.max_missing_pct),
        polygon_per_page_delay_seconds=float(args.polygon_per_page_delay_seconds),
        polygon_rate_limit_sleep_seconds=float(args.polygon_rate_limit_sleep_seconds),
        debug_chunks_dir=Path(args.debug_chunks_dir) if args.debug_chunks_dir else None,
    )

    run(cfg)


if __name__ == "__main__":
    main()
