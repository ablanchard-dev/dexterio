#!/usr/bin/env python3
"""
Point d'entrée documenté : régénère **d'un coup** le manifest campagne + l'agrégat JSON
(arbitraire NF tp1 1.0R vs 1.5R).

Délègue à `aggregate_nf_tp1_arbitration.py`, qui écrit déjà :
- `results/labs/mini_week/_nf_tp1_arbitration_campaign_manifest.json`
- `results/labs/mini_week/_nf_tp1_arbitration_aggregate.json`

Les arguments CLI sont transmis tels quels (ex. `--out-md docs/PHASE_NF_TP1_ARBITRATION_TABLE.md`).

Usage (depuis backend/) :
  .venv/bin/python scripts/regen_nf_tp1_arbitration_artifacts.py
  .venv/bin/python scripts/regen_nf_tp1_arbitration_artifacts.py --out-md docs/PHASE_NF_TP1_ARBITRATION_TABLE.md
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    backend = Path(__file__).resolve().parent.parent
    agg = backend / "scripts" / "aggregate_nf_tp1_arbitration.py"
    return int(subprocess.call([sys.executable, str(agg), *sys.argv[1:]]))


if __name__ == "__main__":
    raise SystemExit(main())
