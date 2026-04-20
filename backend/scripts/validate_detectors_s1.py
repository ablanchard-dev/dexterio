#!/usr/bin/env python3
"""
S1 Detector Validation — FVG + BOS on 5m and 15m

Loads 1 week of SPY 1m data, aggregates to 5m/15m via TimeframeAggregator,
runs detect_fvg() and detect_bos() on each HTF close, and dumps counts + samples.

Usage:
  cd backend && .venv/bin/python scripts/validate_detectors_s1.py
  .venv/bin/python scripts/validate_detectors_s1.py --start 2025-11-03 --end 2025-11-09
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.patterns.ict import ICTPatternEngine
from engines.timeframe_aggregator import TimeframeAggregator
from models.market_data import Candle
from utils.path_resolver import historical_data_path


def load_candles(symbol: str, start: str, end: str) -> list[Candle]:
    """Load 1m candles from parquet, filtered to [start, end]."""
    path = historical_data_path("1m", f"{symbol}.parquet")
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    df = pd.read_parquet(path)
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
    if "__index_level_0__" in df.columns and "datetime" not in df.columns:
        df["datetime"] = pd.to_datetime(df["__index_level_0__"], utc=True)
        df = df.drop(columns=["__index_level_0__"])
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)

    start_dt = pd.Timestamp(start, tz="UTC")
    end_dt = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    df = df[(df["datetime"] >= start_dt) & (df["datetime"] < end_dt)]
    df = df.sort_values("datetime").reset_index(drop=True)

    candles = []
    for _, row in df.iterrows():
        candles.append(Candle(
            symbol=symbol,
            timeframe="1m",
            timestamp=row["datetime"].to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume", 0)),
        ))
    print(f"[INFO] Loaded {len(candles)} 1m candles for {symbol} ({start} → {end})")
    return candles


def main():
    parser = argparse.ArgumentParser(description="S1 detector validation (FVG + BOS on 5m/15m)")
    parser.add_argument("--start", default="2025-11-03", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2025-11-09", help="End date YYYY-MM-DD")
    parser.add_argument("--symbol", default="SPY", help="Symbol (default SPY)")
    parser.add_argument("--samples", type=int, default=5, help="Number of sample detections to print per category")
    args = parser.parse_args()

    candles = load_candles(args.symbol, args.start, args.end)
    if not candles:
        print("[ERROR] No candles loaded")
        return 1

    engine = ICTPatternEngine()
    aggregator = TimeframeAggregator()

    # Counters (keys built dynamically as detector_tf_direction, e.g. fvg_5m_bullish)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total: dict[str, int] = defaultdict(int)

    # Sample storage
    samples: dict[str, list] = defaultdict(list)

    bars_5m = 0
    bars_15m = 0

    for candle in candles:
        events = aggregator.add_1m_candle(candle)

        if events["is_close_5m"]:
            bars_5m += 1
            c5 = aggregator.candles_5m.get(args.symbol, [])
            if len(c5) >= 10:
                fvgs = engine.detect_fvg(c5[-100:], "5m")
                for f in fvgs:
                    key = f"fvg_5m_{f.direction}"
                    total[key] += 1
                    date_str = candle.timestamp.strftime("%Y-%m-%d")
                    counts[key][date_str] = counts[key].get(date_str, 0) + 1
                    if len(samples[key]) < args.samples:
                        samples[key].append({
                            "ts": candle.timestamp.isoformat(),
                            "direction": f.direction,
                            "top": f.details.get("top"),
                            "bottom": f.details.get("bottom"),
                            "size_pct": round(f.details.get("size_pct", 0), 4),
                            "strength": round(f.strength, 3),
                        })

                bos_list = engine.detect_bos(c5[-100:], "5m")
                for b in bos_list:
                    key = f"bos_5m_{b.direction}"
                    total[key] += 1
                    date_str = candle.timestamp.strftime("%Y-%m-%d")
                    counts[key][date_str] = counts[key].get(date_str, 0) + 1
                    if len(samples[key]) < args.samples:
                        samples[key].append({
                            "ts": candle.timestamp.isoformat(),
                            "direction": b.direction,
                            "strength": round(b.strength, 3),
                            "pivot_broken": b.details.get("pivot_high_broken") or b.details.get("pivot_low_broken"),
                            "close": b.details.get("close_price"),
                        })

        if events["is_close_15m"]:
            bars_15m += 1
            c15 = aggregator.candles_15m.get(args.symbol, [])
            if len(c15) >= 10:
                fvgs = engine.detect_fvg(c15[-100:], "15m")
                for f in fvgs:
                    key = f"fvg_15m_{f.direction}"
                    total[key] += 1
                    date_str = candle.timestamp.strftime("%Y-%m-%d")
                    counts[key][date_str] = counts[key].get(date_str, 0) + 1
                    if len(samples[key]) < args.samples:
                        samples[key].append({
                            "ts": candle.timestamp.isoformat(),
                            "direction": f.direction,
                            "top": f.details.get("top"),
                            "bottom": f.details.get("bottom"),
                            "size_pct": round(f.details.get("size_pct", 0), 4),
                            "strength": round(f.strength, 3),
                        })

                bos_list = engine.detect_bos(c15[-100:], "15m")
                for b in bos_list:
                    key = f"bos_15m_{b.direction}"
                    total[key] += 1
                    date_str = candle.timestamp.strftime("%Y-%m-%d")
                    counts[key][date_str] = counts[key].get(date_str, 0) + 1
                    if len(samples[key]) < args.samples:
                        samples[key].append({
                            "ts": candle.timestamp.isoformat(),
                            "direction": b.direction,
                            "strength": round(b.strength, 3),
                            "pivot_broken": b.details.get("pivot_high_broken") or b.details.get("pivot_low_broken"),
                            "close": b.details.get("close_price"),
                        })

    # Print results
    print("\n" + "=" * 70)
    print(f"S1 DETECTOR VALIDATION — {args.symbol} {args.start} → {args.end}")
    print(f"Bars processed: 1m={len(candles)}, 5m={bars_5m}, 15m={bars_15m}")
    print("=" * 70)

    for key in sorted(total.keys()):
        parts = key.split("_", 2)
        label = key.upper().replace("_", " ", 2)
        print(f"\n[{label}] Total detections: {total[key]}")
        daily = counts[key]
        if daily:
            for d in sorted(daily.keys()):
                print(f"  {d}: {daily[d]}")
        else:
            print("  (none)")

        if samples[key]:
            print(f"  --- Samples (first {len(samples[key])}) ---")
            for s in samples[key]:
                print(f"    {json.dumps(s)}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for key in sorted(total.keys()):
        print(f"  {key:25s}: {total.get(key, 0):6d}")

    # Gate verdict
    print("\n--- GATE S1 VERDICT ---")
    fvg_5m_total = total.get("fvg_5m_bullish", 0) + total.get("fvg_5m_bearish", 0)
    bos_5m_total = total.get("bos_5m_bullish", 0) + total.get("bos_5m_bearish", 0)
    bos_15m_total = total.get("bos_15m_bullish", 0) + total.get("bos_15m_bearish", 0)

    fvg_5m_ok = fvg_5m_total > 0
    bos_5m_ok = bos_5m_total > 0
    bos_15m_ok = bos_15m_total > 0

    print(f"  FVG 5m:  {'PASS' if fvg_5m_ok else 'FAIL'} ({fvg_5m_total} detections)")
    print(f"  BOS 5m:  {'PASS' if bos_5m_ok else 'FAIL'} ({bos_5m_total} detections)")
    print(f"  BOS 15m: {'PASS' if bos_15m_ok else 'FAIL'} ({bos_15m_total} detections)")

    all_pass = fvg_5m_ok and bos_5m_ok and bos_15m_ok
    print(f"\n  Gate S1: {'ALL PASS' if all_pass else 'FAIL — fix failing detectors before continuing'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
