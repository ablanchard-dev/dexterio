#!/usr/bin/env python3
"""
Verdict gate à partir de `mini_lab_summary_*.json` (+ option `run_manifest.json`).

Usage (depuis backend/) :
  .venv/bin/python scripts/campaign_gate_verdict.py \\
    results/labs/mini_week/202511_w01/mini_lab_summary_202511_w01.json

  .venv/bin/python scripts/campaign_gate_verdict.py summary.json --manifest run_manifest.json \\
    --require-manifest-coverage --require-trade-metrics --out verdict.json

  .venv/bin/python scripts/campaign_gate_verdict.py --manifest-only run_manifest.json

Exit 0 si verdict != NOT_READY, 1 si NOT_READY, 2 si erreur fichier.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.campaign_gate_verdict import verdict_from_manifest_path, verdict_from_paths  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Verdict gate campagne (lecture JSON)")
    p.add_argument(
        "summary",
        type=str,
        nargs="?",
        default=None,
        help="mini_lab_summary_*.json (omit avec --manifest-only)",
    )
    p.add_argument("--manifest", type=str, default=None)
    p.add_argument(
        "--manifest-only",
        type=str,
        default=None,
        metavar="PATH",
        help="Uniquement run_manifest.json (synthèse partielle ; trade_metrics exigent un summary)",
    )
    p.add_argument("--require-manifest-coverage", action="store_true")
    p.add_argument("--require-trade-metrics", action="store_true")
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

    try:
        if args.manifest_only:
            rep = verdict_from_manifest_path(
                args.manifest_only,
                require_manifest_coverage=args.require_manifest_coverage,
                require_trade_metrics=args.require_trade_metrics,
            )
        else:
            if not args.summary:
                print("ERROR: fournir summary.json ou --manifest-only", file=sys.stderr)
                return 2
            rep = verdict_from_paths(
                args.summary,
                args.manifest,
                require_manifest_coverage=args.require_manifest_coverage,
                require_trade_metrics=args.require_trade_metrics,
            )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON {e}", file=sys.stderr)
        return 2

    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", flush=True)
    else:
        print(text)

    return 1 if rep.get("verdict") == "NOT_READY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
