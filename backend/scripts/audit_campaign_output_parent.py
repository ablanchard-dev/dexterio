#!/usr/bin/env python3
"""
Audit des artefacts sous `results/labs/mini_week/<output_parent>/`.

Pour chaque sous-dossier : `mini_lab_summary*.json`, `run_manifest.json`, champs couverture.
Si `walk_forward_campaign.json` est présent : `max_returncode`, `fail_fast_stopped`.

Usage (depuis backend/) :
  .venv/bin/python scripts/audit_campaign_output_parent.py --output-parent phase_b_nf_tp1rr_1p00
  .venv/bin/python scripts/audit_campaign_output_parent.py --output-parent wf_aug_nov --strict

Exit 0 si overall_ok, 1 sinon, 2 si dossier absent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.campaign_output_audit import audit_output_parent  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Audit campagne mini_week output_parent")
    p.add_argument("--output-parent", type=str, required=True)
    p.add_argument(
        "--results-root",
        type=str,
        default=None,
        help="Racine results (défaut: backend/results)",
    )
    p.add_argument("--strict", action="store_true", help="Exit 2 si base absente ou aucun sous-dossier run")
    p.add_argument(
        "--allow-empty",
        action="store_true",
        help="Exit 0 si aucun run (sinon exit 1 quand run_count=0)",
    )
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

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
