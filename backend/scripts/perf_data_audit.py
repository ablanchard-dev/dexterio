"""Sprint perf: audit rapide qualité données intraday (SPY/QQQ)."""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.quality_gates import compute_daily_missing_bars  # noqa: E402
from utils.path_resolver import historical_data_path, results_path  # noqa: E402


def _audit_symbol(symbol: str, lookback_days: int) -> Dict[str, Any]:
    p = historical_data_path("1m", f"{symbol}.parquet")
    if not p.exists():
        return {"symbol": symbol, "exists": False}

    df = pd.read_parquet(p)
    if "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
        df = df.copy()
        df["datetime"] = dt
    else:
        idx = pd.to_datetime(df.index, utc=True, errors="coerce")
        df = df.reset_index(drop=True)
        df["datetime"] = idx

    df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    dup = int(df["datetime"].duplicated().sum())
    data_end_date = df["datetime"].max().date()
    end = data_end_date + timedelta(days=1)
    start = max(data_end_date - timedelta(days=lookback_days), df["datetime"].min().date())
    daily, corrupted = compute_daily_missing_bars(df, start=start, end=end, max_missing_pct=5.0)

    return {
        "symbol": symbol,
        "exists": True,
        "rows": int(len(df)),
        "duplicates": dup,
        "start_utc": df["datetime"].min().isoformat() if len(df) else None,
        "end_utc": df["datetime"].max().isoformat() if len(df) else None,
        "lookback_days": lookback_days,
        "corrupted_days_count": len(corrupted),
        "corrupted_days_sample": corrupted[:10],
        "daily_missing_sample": daily[:10],
    }


def main() -> None:
    symbols: List[str] = ["SPY", "QQQ"]
    out = {"generated_at": pd.Timestamp.utcnow().isoformat(), "symbols": []}
    for s in symbols:
        out["symbols"].append(_audit_symbol(s, lookback_days=60))
    out_file = results_path("perf_data_audit.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[perf] data audit: {out_file}")


if __name__ == "__main__":
    main()

