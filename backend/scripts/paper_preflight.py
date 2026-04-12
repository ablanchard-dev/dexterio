#!/usr/bin/env python3
"""CLI pré-lancement paper supervisé (preflight). Voir `utils/paper_preflight.py`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permet `python scripts/paper_preflight.py` depuis backend/
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from utils.paper_preflight import collect_preflight  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Preflight paper supervisé (Git + venv)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Code retour 2 si working tree non propre (sinon avertissement seulement).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Sortie JSON sur stdout (avertissements inclus).",
    )
    args = p.parse_args()

    try:
        r = collect_preflight(cwd=Path.cwd())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    warns = r.warnings()
    payload = {
        "repo_root": str(r.repo_root),
        "git_sha": r.git_sha,
        "working_tree_clean": r.is_clean,
        "dirty_count": len(r.dirty_paths),
        "venv_python": str(r.venv_python) if r.venv_python else None,
        "warnings": warns,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"repo_root={r.repo_root}")
        print(f"git_sha={r.git_sha}")
        print(f"working_tree_clean={r.is_clean} (dirty_count={len(r.dirty_paths)})")
        if r.venv_python:
            print(f"venv_python={r.venv_python}")
        for w in warns:
            print(f"WARNING: {w}", file=sys.stderr)

    if args.strict and not r.is_clean:
        print("ERROR: --strict et working tree non propre.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
