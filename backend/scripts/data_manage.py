"""data_manage.py — S+2 P0 CLI for data lifecycle.

3 commandes (frozen scope) :
  - download-prices : fetch + save OHLCV daily for a list of symbols
  - download-earnings : fetch + save earnings dates + EPS surprise
  - check-quality : run quality report on a saved dataset

Usage examples :
  python scripts/data_manage.py download-prices --symbols AAPL MSFT \\
      --start 2019-06-01 --end 2025-11-30 --out data/equities/sample.parquet

  python scripts/data_manage.py download-earnings --symbols AAPL MSFT \\
      --start 2019-06-01 --end 2025-11-30 --out data/earnings/sample.parquet

  python scripts/data_manage.py check-quality --path data/equities/sample.parquet --type prices
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Add backend dir to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from providers.yahoo_price_provider import YahooPriceProvider
from providers.yahoo_earnings_provider import YahooEarningsProvider
from providers import read_manifest
from research.quality_report import check_prices_quality, check_earnings_quality


def _parse_symbols(symbols_arg: list[str], symbols_file: str | None) -> list[str]:
    """Resolve symbols from CLI args OR text file (one per line)."""
    if symbols_file:
        path = Path(symbols_file)
        if not path.exists():
            print(f"ERROR: symbols file not found: {symbols_file}", file=sys.stderr)
            sys.exit(2)
        symbols = [s.strip().upper() for s in path.read_text().splitlines()
                   if s.strip() and not s.startswith("#")]
        return symbols
    return [s.upper() for s in (symbols_arg or [])]


def cmd_download_prices(args: argparse.Namespace) -> int:
    symbols = _parse_symbols(args.symbols, args.symbols_file)
    if not symbols:
        print("ERROR: no symbols provided", file=sys.stderr)
        return 2

    out_path = Path(args.out).resolve()
    print(f"[download-prices] {len(symbols)} symbols, {args.start} → {args.end}")
    print(f"  output : {out_path}")

    p = YahooPriceProvider()
    df = p.fetch(symbols, args.start, args.end)
    if df.empty:
        print("WARNING: no data returned")
        return 1

    # Quality report attached to manifest warnings
    qr = check_prices_quality(df, dataset_path=str(out_path), expected_end=args.end)
    print(qr)
    warnings_list = qr.warnings + [f"FAIL: {f}" for f in qr.fails]

    data_path, manifest_path = p.save(
        df, out_path,
        symbols=symbols, start=args.start, end=args.end,
        warnings=warnings_list,
        extra={"quality_status": qr.status, "quality_stats": qr.stats},
    )
    print(f"[download-prices] saved {len(df):,} rows → {data_path.name}")
    print(f"[download-prices] manifest → {manifest_path.name}")
    return 0 if qr.status != "FAIL" else 1


def cmd_download_earnings(args: argparse.Namespace) -> int:
    symbols = _parse_symbols(args.symbols, args.symbols_file)
    if not symbols:
        print("ERROR: no symbols provided", file=sys.stderr)
        return 2

    out_path = Path(args.out).resolve()
    print(f"[download-earnings] {len(symbols)} symbols, {args.start} → {args.end}")
    print(f"  use_batch_fallback={args.batch}")

    p = YahooEarningsProvider(use_batch_fallback=args.batch)
    df = p.fetch(symbols, args.start, args.end)
    if df.empty:
        print("WARNING: no earnings data returned")
        return 1

    qr = check_earnings_quality(df, dataset_path=str(out_path))
    print(qr)
    warnings_list = qr.warnings + [f"FAIL: {f}" for f in qr.fails]

    data_path, manifest_path = p.save(
        df, out_path,
        symbols=symbols, start=args.start, end=args.end,
        warnings=warnings_list,
        extra={"quality_status": qr.status, "quality_stats": qr.stats,
               "use_batch_fallback": args.batch},
    )
    print(f"[download-earnings] saved {len(df):,} rows → {data_path.name}")
    print(f"[download-earnings] manifest → {manifest_path.name}")
    return 0 if qr.status != "FAIL" else 1


def cmd_check_quality(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    df = pd.read_parquet(path)
    print(f"[check-quality] loaded {len(df):,} rows from {path}")

    if args.type == "prices":
        qr = check_prices_quality(df, dataset_path=str(path))
    elif args.type == "earnings":
        qr = check_earnings_quality(df, dataset_path=str(path))
    else:
        print(f"ERROR: unknown type {args.type}", file=sys.stderr)
        return 2

    print(qr)

    # Read manifest if present
    m = read_manifest(path)
    if m:
        print()
        print("=== Manifest sidecar ===")
        print(json.dumps(m, indent=2, default=str))

    return 0 if qr.status != "FAIL" else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DexterioBOT data lifecycle CLI (S+2 P0 minimal)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # download-prices
    p1 = sub.add_parser("download-prices",
                          help="Fetch + save OHLCV daily prices via yfinance")
    p1.add_argument("--symbols", nargs="*",
                     help="Tickers to fetch (e.g. AAPL MSFT)")
    p1.add_argument("--symbols-file",
                     help="Text file with one ticker per line")
    p1.add_argument("--start", required=True, help="YYYY-MM-DD")
    p1.add_argument("--end", required=True, help="YYYY-MM-DD")
    p1.add_argument("--out", required=True, help="Output parquet path")
    p1.set_defaults(fn=cmd_download_prices)

    # download-earnings
    p2 = sub.add_parser("download-earnings",
                          help="Fetch + save earnings dates + EPS surprise")
    p2.add_argument("--symbols", nargs="*", help="Tickers to fetch")
    p2.add_argument("--symbols-file",
                     help="Text file with one ticker per line")
    p2.add_argument("--start", required=True, help="YYYY-MM-DD")
    p2.add_argument("--end", required=True, help="YYYY-MM-DD")
    p2.add_argument("--out", required=True, help="Output parquet path")
    p2.add_argument("--batch", action="store_true",
                     help="Use yahooquery batch (4Q only) instead of yfinance per-ticker (~25Q)")
    p2.set_defaults(fn=cmd_download_earnings)

    # check-quality
    p3 = sub.add_parser("check-quality",
                          help="Run quality report on a saved dataset + display manifest")
    p3.add_argument("--path", required=True, help="Path to parquet file")
    p3.add_argument("--type", choices=["prices", "earnings"], required=True,
                     help="Dataset type")
    p3.set_defaults(fn=cmd_check_quality)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
