#!/usr/bin/env python3
"""
Preflight données avant backtest long (1m SPY/QQQ).

Vérifie couverture temporelle + trous grossiers — même esprit que Freqtrade « data ok ».
Ne lance pas le moteur.

Usage (depuis backend/) :
  .venv/bin/python scripts/backtest_data_preflight.py --start 2025-01-01 --end 2025-01-31
  .venv/bin/python scripts/backtest_data_preflight.py --start 2025-06-01 --end 2026-01-01 --warmup-days 30 --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from utils.backtest_data_coverage import check_backtest_data_coverage  # noqa: E402
from utils.path_resolver import discover_symbol_parquet, historical_data_path  # noqa: E402


def _paths_for_symbols(symbols: list[str]) -> list[str]:
    out: list[str] = []
    for sym in symbols:
        p = discover_symbol_parquet(sym, "1m")
        if p is None:
            p = historical_data_path("1m", f"{sym}.parquet")
        out.append(str(p))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Preflight couverture parquet 1m pour backtest")
    p.add_argument("--start", type=str, required=True)
    p.add_argument("--end", type=str, required=True)
    p.add_argument("--symbols", type=str, default="SPY,QQQ")
    p.add_argument("--warmup-days", type=int, default=30)
    p.add_argument(
        "--max-gap-warn",
        type=float,
        default=6.0,
        help="Avertir si écart max entre barres > N minutes (0 = désactiver)",
    )
    p.add_argument("--strict", action="store_true", help="Code 2 si warnings (trous data)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    paths = _paths_for_symbols(symbols)
    gap = None if args.max_gap_warn <= 0 else args.max_gap_warn
    rep = check_backtest_data_coverage(
        data_paths=paths,
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        htf_warmup_days=args.warmup_days,
        max_gap_warn_minutes=gap,
    )

    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"ok={rep['ok']} warmup_start={rep['warmup_start_utc']} end_excl={rep['end_exclusive_utc']}")
        for e in rep["errors"]:
            print(f"ERROR: {e}", file=sys.stderr)
        for w in rep["warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)

    if not rep["ok"]:
        return 1
    if args.strict and rep["warnings"]:
        print("ERROR: --strict et warnings présents", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
