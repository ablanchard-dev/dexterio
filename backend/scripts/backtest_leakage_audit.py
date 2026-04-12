#!/usr/bin/env python3
"""
Audits légers hors hot path : cohérence temporelle trades, OHLCV monotonic, option data window.

Usage (depuis backend/) :
  .venv/bin/python scripts/backtest_leakage_audit.py --trades-parquet path/to/trades.parquet
  .venv/bin/python scripts/backtest_leakage_audit.py --data-parquet data/1m/SPY.parquet
  .venv/bin/python scripts/backtest_leakage_audit.py \\
    --data-parquet data/1m/SPY.parquet --data-parquet data/1m/QQQ.parquet \\
    --symbols SPY,QQQ --start 2025-11-01 --end 2025-11-30 --warmup-days 30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.backtest_leakage_audit import (  # noqa: E402
    audit_ohlcv_parquet_monotonic,
    audit_trades_parquet_temporal,
    run_backtest_leakage_audit_bundle,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Audits anti-leakage / cohérence (léger)")
    p.add_argument("--trades-parquet", type=str, default=None)
    p.add_argument(
        "--data-parquet",
        action="append",
        default=None,
        help="Répétable ; avec --start/--end/--symbols déclenche aussi coverage fenêtre",
    )
    p.add_argument("--symbols", type=str, default=None, help="ex. SPY,QQQ (ordre aligné sur --data-parquet)")
    p.add_argument("--start", type=str, default=None)
    p.add_argument("--end", type=str, default=None)
    p.add_argument("--warmup-days", type=int, default=0)
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

    dps = args.data_parquet or []
    if not args.trades_parquet and not dps:
        print("ERROR: fournir --trades-parquet et/ou --data-parquet", file=sys.stderr)
        return 2

    if args.start and args.end and args.symbols and dps:
        syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        if len(syms) != len(dps):
            print("ERROR: --symbols et nombre de --data-parquet doivent coïncider", file=sys.stderr)
            return 2
        rep = run_backtest_leakage_audit_bundle(
            trades_parquet=args.trades_parquet,
            data_parquets=dps,
            symbols=syms,
            start_date=args.start,
            end_date=args.end,
            htf_warmup_days=args.warmup_days,
        )
    else:
        parts: dict = {}
        if args.trades_parquet:
            parts["trades_temporal"] = audit_trades_parquet_temporal(args.trades_parquet)
        if dps:
            parts["data_ohlcv"] = [audit_ohlcv_parquet_monotonic(x) for x in dps]
        ok = True
        for v in parts.values():
            if isinstance(v, dict) and v.get("ok") is False:
                ok = False
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict) and it.get("ok") is False:
                        ok = False
        rep = {"schema_version": "BacktestLeakageAuditBundleV0", "ok": ok, "parts": parts}

    text = json.dumps(rep, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", flush=True)
    else:
        print(text)
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
