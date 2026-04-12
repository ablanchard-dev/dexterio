#!/usr/bin/env python3
"""
Precheck consolidé paper supervisé : Git/venv + rappels + optionnellement rapport parquet.

Compose `paper_preflight` et, si demandé, `run_parquet_analyzer_bundle` sur un trades parquet.
Ne lance pas le moteur de backtest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backtest.trade_parquet_analyzer_bundle import run_parquet_analyzer_bundle  # noqa: E402
from utils.paper_preflight import collect_preflight  # noqa: E402

_REMINDERS: List[str] = [
    "Données 1m SPY/QQQ : couvrir la fenêtre du run (voir path_resolver / discover_symbol_parquet).",
    "YAML : NY_Open_Reversal intact ; News_Fade tp1 seulement après gate arbitrage (CORE_PAPER_NOW_LAUNCH.md).",
    "Après campagne nf_tp1_arb : scripts/regen_nf_tp1_arbitration_artifacts.py pour manifest + agrégat alignés.",
    "Nouveaux runs mini-lab : run_manifest.lab_environment inclut data_fingerprint_v0 (sauf DEXTERIO_OMIT_DATA_FINGERPRINT=1).",
]


def _preflight_payload(strict_clean: bool) -> Dict[str, Any]:
    r = collect_preflight(cwd=Path.cwd())
    warns = r.warnings()
    return {
        "repo_root": str(r.repo_root),
        "git_sha": r.git_sha,
        "working_tree_clean": r.is_clean,
        "dirty_count": len(r.dirty_paths),
        "venv_python": str(r.venv_python) if r.venv_python else None,
        "preflight_warnings": warns,
        "strict_clean_requested": strict_clean,
        "strict_clean_failed": strict_clean and not r.is_clean,
        "reminders": list(_REMINDERS),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Precheck paper supervisé (preflight + rappels + option parquet)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Code 2 si working tree non propre.",
    )
    p.add_argument("--json", action="store_true", help="Une seule sortie JSON stdout.")
    p.add_argument(
        "--trades-parquet",
        type=str,
        default="",
        help="Optionnel : chemin trades .parquet pour analyzer bundle.",
    )
    p.add_argument("--playbook", type=str, default="", help="Filtre playbook pour le bundle.")
    p.add_argument(
        "--analyzers",
        type=str,
        default="summary_r,exit_reason_mix,playbook_counts",
        help="Analyzers du bundle (virgules).",
    )
    args = p.parse_args()

    payload: Dict[str, Any] = _preflight_payload(args.strict)

    bundle: Optional[Dict[str, Any]] = None
    tpath = args.trades_parquet.strip()
    if tpath:
        names = [x.strip() for x in args.analyzers.split(",") if x.strip()]
        playbook_f = args.playbook.strip() or None
        bundle = run_parquet_analyzer_bundle(tpath, playbook=playbook_f, names=names)
    payload["trades_bundle"] = bundle

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"git_sha={payload['git_sha']} clean={payload['working_tree_clean']} dirty={payload['dirty_count']}")
        for w in payload["preflight_warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)
        for line in payload["reminders"]:
            print(f"REMINDER: {line}")
        if bundle is not None:
            print("--- trades bundle ---")
            print(json.dumps(bundle, indent=2, default=str))

    if payload["strict_clean_failed"]:
        print("ERROR: --strict et working tree non propre.", file=sys.stderr)
        return 2
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
