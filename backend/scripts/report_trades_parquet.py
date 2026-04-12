#!/usr/bin/env python3
"""Rapport analyzers sur un parquet trades (JSON ou texte). Voir `backtest/trade_parquet_analyzer_bundle.py`."""
from __future__ import annotations

import argparse
import json
import pprint
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backtest.trade_parquet_analyzer_bundle import list_analyzers, run_parquet_analyzer_bundle  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(
        description="Exécute le bundle d'analyzers sur un fichier trades parquet."
    )
    p.add_argument(
        "parquet",
        type=str,
        nargs="?",
        default="",
        help="Chemin vers le fichier .parquet (requis sauf si --list-analyzers).",
    )
    p.add_argument("--playbook", type=str, default="", help="Filtre playbook (optionnel).")
    p.add_argument(
        "--analyzers",
        type=str,
        default="summary_r,exit_reason_mix,playbook_counts",
        help="Liste d'analyzers séparés par des virgules.",
    )
    p.add_argument(
        "--list-analyzers",
        action="store_true",
        help="Affiche les clés enregistrées et quitte.",
    )
    p.add_argument("--json", action="store_true", help="Sortie JSON sur stdout.")
    args = p.parse_args()

    if args.list_analyzers:
        payload = {"analyzers": list(list_analyzers())}
        print(json.dumps(payload, indent=2))
        return 0

    if not args.parquet.strip():
        p.error("chemin parquet requis (ou utiliser --list-analyzers)")

    names = [x.strip() for x in args.analyzers.split(",") if x.strip()]
    playbook_f = args.playbook.strip() or None
    out = run_parquet_analyzer_bundle(args.parquet, playbook=playbook_f, names=names)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        pprint.pprint(out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1) from e
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2) from e
