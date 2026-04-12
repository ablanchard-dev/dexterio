#!/usr/bin/env python3
"""
Agrège les `mini_lab_summary*.json` d’une campagne (nested ou flat).

Usage (depuis backend/) :
  .venv/bin/python scripts/rollup_campaign_summaries.py --output-parent phase_b_nf_tp1rr_1p00
  .venv/bin/python scripts/rollup_campaign_summaries.py --path results/labs/mini_week/202511_w01

Exit 0 si exécution OK ; 2 avec --fail-if-not-exists si dossier absent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.campaign_rollup import rollup_summaries_under_base  # noqa: E402
from utils.path_resolver import results_path  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Rollup mini_lab_summary par campagne")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output-parent", type=str)
    g.add_argument("--path", type=str)
    p.add_argument("--results-root", type=str, default=None)
    p.add_argument("--out", type=str, default=None)
    p.add_argument(
        "--fail-if-not-exists",
        action="store_true",
        help="Exit 2 si le dossier base n’existe pas",
    )
    args = p.parse_args()

    if args.path:
        base = Path(args.path).expanduser().resolve()
        logical = base.name
    else:
        if not args.output_parent:
            print("ERROR: --output-parent requis", file=sys.stderr)
            return 2
        logical = args.output_parent
        rb = Path(args.results_root).resolve() if args.results_root else None
        base = (rb / "labs" / "mini_week" / logical) if rb else results_path("labs", "mini_week", logical)

    if args.fail_if_not_exists and not base.is_dir():
        print(f"ERROR: not a directory: {base}", file=sys.stderr)
        return 2

    rep = rollup_summaries_under_base(base, logical_name=logical)

    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", flush=True)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
