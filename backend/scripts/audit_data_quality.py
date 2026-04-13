"""Audit data quality 1m for symbols and date range."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import historical_data_path


def _load_df(symbol: str) -> pd.DataFrame:
    p = historical_data_path("1m", f"{symbol}.parquet")
    df = pd.read_parquet(p)
    if "datetime" in df.columns:
        ts = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    else:
        ts = pd.to_datetime(df.index, utc=True, errors="coerce")
    out = df.copy()
    out["__dt"] = ts
    return out


def _audit_symbol(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    m = (df["__dt"] >= start) & (df["__dt"] <= end)
    d = df.loc[m].copy().sort_values("__dt")

    gaps = d["__dt"].diff().dropna().dt.total_seconds()
    ohlc_bad = (
        (d["high"] < d[["open", "close", "low"]].max(axis=1))
        | (d["low"] > d[["open", "close", "high"]].min(axis=1))
    )

    return {
        "rows": int(len(d)),
        "start": str(d["__dt"].min()) if len(d) else None,
        "end": str(d["__dt"].max()) if len(d) else None,
        "dup_timestamps": int(d["__dt"].duplicated().sum()),
        "monotonic_non_decreasing": bool((d["__dt"].diff().dropna().dt.total_seconds() >= 0).all()) if len(d) > 1 else True,
        "ohlc_invalid_rows": int(ohlc_bad.sum()),
        "gaps_gt_60s": int((gaps > 60).sum()) if len(gaps) else 0,
        "gaps_gt_300s": int((gaps > 300).sum()) if len(gaps) else 0,
        "max_gap_seconds": float(gaps.max()) if len(gaps) else 0.0,
        "tz_aware": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Audit 1m data quality")
    p.add_argument("--symbols", default="SPY,QQQ")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")

    out = {
        "range": {"start": str(start), "end": str(end)},
        "symbols": {},
    }

    for sym in [x.strip().upper() for x in args.symbols.split(",") if x.strip()]:
        df = _load_df(sym)
        out["symbols"][sym] = _audit_symbol(df, start, end)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
