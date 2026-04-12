#!/usr/bin/env python3
"""
Écrit un `playbooks.yml` dérivé : seul News_Fade tp1_rr / min_rr change (PHASE B util).
Vérifie NY_Open_Reversal inchangé vs canonique.

Usage (depuis backend/) :
  .venv/bin/python scripts/write_nf_tp1_derived_yaml.py --tp1-rr 1.0
  .venv/bin/python scripts/write_nf_tp1_derived_yaml.py --tp1-rr 1.5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path
from utils.phase_b_nf_tp1_yaml import (
    CANONICAL_PLAYBOOKS,
    assert_ny_unchanged_after_sweep,
    nf_tp1_rr_tag,
    write_nf_tp1_sweep_yaml,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tp1-rr", type=float, required=True, help="Ex. 1.0 ou 1.5")
    args = p.parse_args()
    tag = nf_tp1_rr_tag(args.tp1_rr)
    dest = results_path("labs", "mini_week", "_phase_b_yamls", f"playbooks_nf_tp1_{tag}.yml")
    write_nf_tp1_sweep_yaml(
        canonical_path=CANONICAL_PLAYBOOKS,
        dest_path=dest,
        tp1_rr=float(args.tp1_rr),
    )
    assert_ny_unchanged_after_sweep(canonical_path=CANONICAL_PLAYBOOKS, derived_path=dest)
    print(f"[nf_tp1_yaml] wrote {dest} (News_Fade min_rr=tp1_rr={args.tp1_rr})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
