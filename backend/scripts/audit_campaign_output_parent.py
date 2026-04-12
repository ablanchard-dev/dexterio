#!/usr/bin/env python3
"""
Audit des artefacts mini-lab sous `labs/mini_week/`.

Détection automatique :

- **nested** : `.../<output_parent>/<label>/mini_lab_summary*.json` (campagnes multi-runs).
- **flat** : `.../mini_week/<label>/mini_lab_summary*.json` directement (run seul).

`walk_forward_campaign.json` s’il est présent au même niveau que les runs audités.

Usage (depuis backend/) :
  .venv/bin/python scripts/audit_campaign_output_parent.py --output-parent phase_b_nf_tp1rr_1p00
  .venv/bin/python scripts/audit_campaign_output_parent.py --path results/labs/mini_week/202511_w01

Exit 0 si overall_ok, 1 sinon, 2 avec --strict si base absente ou aucun run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.campaign_output_audit import audit_campaign_base, audit_output_parent  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Audit campagne mini_week (nested ou flat)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--output-parent",
        type=str,
        help="Nom sous results/labs/mini_week/<output_parent>/",
    )
    g.add_argument(
        "--path",
        type=str,
        help="Chemin direct vers le dossier à auditer (relatif au cwd ou absolu)",
    )
    p.add_argument(
        "--results-root",
        type=str,
        default=None,
        help="Avec --output-parent uniquement : racine results (défaut: backend/results)",
    )
    p.add_argument("--strict", action="store_true", help="Exit 2 si base absente ou aucun run")
    p.add_argument(
        "--allow-empty",
        action="store_true",
        help="Exit 0 si aucun run (sinon exit 1 quand run_count=0)",
    )
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

    if args.path:
        base = Path(args.path).expanduser().resolve()
        rep = audit_campaign_base(base, logical_name=base.name)
    else:
        if not args.output_parent:
            print("ERROR: --output-parent requis", file=sys.stderr)
            return 2
        rb = Path(args.results_root).resolve() if args.results_root else None
        rep = audit_output_parent(args.output_parent, results_base=rb)

    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", flush=True)
    else:
        print(text)

    if args.allow_empty and rep["run_count"] == 0:
        return 0
    if args.strict and (not rep["base_exists"] or rep["run_count"] == 0):
        return 2
    return 0 if rep.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
