#!/usr/bin/env python3
"""
Walk-forward léger : émet uniquement des fenêtres train/test (2 splits OOS), sans moteur.

Usage (depuis backend/) :
  .venv/bin/python scripts/walk_forward_light.py --start 2025-08-01 --end 2025-11-30
  .venv/bin/python scripts/walk_forward_light.py --start 2025-08-01 --end 2025-11-30 --out wf.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.walk_forward_light import walk_forward_two_splits_expanding  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Walk-forward 2 splits (calendrier seul)")
    p.add_argument("--start", type=str, required=True, help="YYYY-MM-DD inclusif")
    p.add_argument("--end", type=str, required=True, help="YYYY-MM-DD inclusif")
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()
    try:
        rep = walk_forward_two_splits_expanding(args.start, args.end)
    except ValueError as e:
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
