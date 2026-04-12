#!/usr/bin/env python3
"""
Preflight données avant backtest long (1m SPY/QQQ).

Vérifie couverture temporelle + trous grossiers — même esprit que Freqtrade « data ok ».
Ne lance pas le moteur.

Usage (depuis backend/) :
  .venv/bin/python scripts/backtest_data_preflight.py --start 2025-01-01 --end 2025-01-31
  .venv/bin/python scripts/backtest_data_preflight.py --start 2025-06-01 --end 2025-11-28 --warmup-days 30 --ignore-warmup-check
  (Remplacer les dates par des YYYY-MM-DD réels ; <DEBUT>/<FIN> ne sont pas valides.)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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
        default=0.0,
        help="Avertir si écart max entre barres > N minutes (0 = désactiver par défaut)",
    )
    p.add_argument(
        "--gap-all-pairs",
        action="store_true",
        help="Mesurer les écarts sur toutes les paires consécutives (sinon: même jour UTC seulement, évite week-end RTH)",
    )
    p.add_argument(
        "--ignore-warmup-check",
        action="store_true",
        help="Ne pas exiger les jours avant --start pour le warmup HTF (avertissement seulement si incomplet)",
    )
    p.add_argument("--strict", action="store_true", help="Code 2 si warnings (trous data)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    for label, d in (("--start", args.start), ("--end", args.end)):
        if not _DATE_RE.match(d.strip()):
            print(
                f"ERROR: {label} doit être une date YYYY-MM-DD (ex. 2025-06-01), pas un placeholder comme <DEBUT>.",
                file=sys.stderr,
            )
            return 2

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    paths = _paths_for_symbols(symbols)
    gap = None if args.max_gap_warn <= 0 else args.max_gap_warn
    rep = check_backtest_data_coverage(
        data_paths=paths,
        symbols=symbols,
        start_date=args.start.strip(),
        end_date=args.end.strip(),
        htf_warmup_days=args.warmup_days,
        max_gap_warn_minutes=gap,
        gap_same_utc_day_only=not args.gap_all_pairs,
        ignore_warmup_check=args.ignore_warmup_check,
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
