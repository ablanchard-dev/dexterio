#!/usr/bin/env python3
"""
PHASE B — Enchaîne mini-labs nov2025 pour sweep tp1_rr News_Fade uniquement.

Chaque variante = dossier `labs/mini_week/phase_b_nf_tp1rr_<tag>/` + YAML dérivé sous
`labs/mini_week/_phase_b_yamls/`. N'écrase pas `labs/mini_week/202511_w0x/` (baseline).

Usage (depuis backend/) :
  .venv/bin/python scripts/run_mini_lab_phase_b_nf_tp1_sweep.py
  .venv/bin/python scripts/run_mini_lab_phase_b_nf_tp1_sweep.py --skip-existing
"""
from __future__ import annotations

import argparse
import subprocess
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

# Même calendrier que run_mini_lab_multiweek.py preset nov2025
NOV2025_WINDOWS: list[tuple[str, str, str]] = [
    ("2025-11-03", "2025-11-09", "202511_w01"),
    ("2025-11-10", "2025-11-16", "202511_w02"),
    ("2025-11-17", "2025-11-23", "202511_w03"),
    ("2025-11-24", "2025-11-30", "202511_w04"),
]

TP1_VALUES = (1.0, 1.25, 1.5, 2.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="PHASE B sweep tp1_rr News_Fade (nov2025)")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Ignore une fenêtre si mini_lab_summary_<label>.json existe déjà",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="SPY,QQQ",
        help="Transmis à run_mini_lab_week.py",
    )
    args = parser.parse_args()

    yamls_dir = results_path("labs", "mini_week", "_phase_b_yamls")
    yamls_dir.mkdir(parents=True, exist_ok=True)
    week_script = backend_dir / "scripts" / "run_mini_lab_week.py"

    for tp1 in TP1_VALUES:
        tag = nf_tp1_rr_tag(tp1)
        yml_path = yamls_dir / f"playbooks_nf_tp1_{tag}.yml"
        write_nf_tp1_sweep_yaml(
            canonical_path=CANONICAL_PLAYBOOKS,
            dest_path=yml_path,
            tp1_rr=tp1,
        )
        assert_ny_unchanged_after_sweep(canonical_path=CANONICAL_PLAYBOOKS, derived_path=yml_path)
        print(f"[phase_b] wrote {yml_path} (News_Fade tp1_rr=min_rr={tp1})", flush=True)

        output_parent = f"phase_b_nf_tp1rr_{tag}"
        for start, end, label in NOV2025_WINDOWS:
            summary = (
                backend_dir
                / "results"
                / "labs"
                / "mini_week"
                / output_parent
                / label
                / f"mini_lab_summary_{label}.json"
            )
            if args.skip_existing and summary.is_file():
                print(f"[phase_b] skip existing {output_parent}/{label}", flush=True)
                continue
            cmd = [
                sys.executable,
                str(week_script),
                "--start",
                start,
                "--end",
                end,
                "--label",
                label,
                "--symbols",
                args.symbols,
                "--playbooks-yaml",
                str(yml_path),
                "--output-parent",
                output_parent,
                "--nf-tp1-rr",
                str(tp1),
            ]
            print(f"[phase_b] RUN {output_parent} {label} {start}..{end}", flush=True)
            r = subprocess.run(cmd, cwd=str(backend_dir))
            if r.returncode != 0:
                print(f"[phase_b] FAIL {output_parent} {label} exit={r.returncode}", flush=True)
                return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
