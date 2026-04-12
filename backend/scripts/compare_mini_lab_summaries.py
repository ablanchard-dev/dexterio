#!/usr/bin/env python3
"""
Compare deux fichiers `mini_lab_summary_*.json` (funnel, totaux, capital).

Usage (depuis backend/) :
  .venv/bin/python scripts/compare_mini_lab_summaries.py \\
    results/labs/mini_week/202511_w01/mini_lab_summary_202511_w01.json \\
    results/labs/mini_week/202511_w02/mini_lab_summary_202511_w02.json
  .venv/bin/python scripts/compare_mini_lab_summaries.py a.json b.json --out diff.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.mini_lab_summary_compare import compare_mini_lab_summary_files  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Compare deux mini_lab_summary JSON")
    p.add_argument("path_a", type=str)
    p.add_argument("path_b", type=str)
    p.add_argument("--out", type=str, default=None, help="Écrire le JSON (défaut: stdout)")
    args = p.parse_args()

    try:
        rep = compare_mini_lab_summary_files(args.path_a, args.path_b)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    text = json.dumps(rep, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", flush=True)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
