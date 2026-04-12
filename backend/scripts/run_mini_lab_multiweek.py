#!/usr/bin/env python3
"""
Enchaîne plusieurs `run_mini_lab_week.py` (un sous-processus par fenêtre) — même protocole risk.

Usage (depuis backend/) :
  .venv/bin/python scripts/run_mini_lab_multiweek.py --preset nov2025
  .venv/bin/python scripts/run_mini_lab_multiweek.py --preset nov2025 --skip-existing
  .venv/bin/python scripts/run_mini_lab_multiweek.py --no-aggregate   # ne lance pas l’agrégateur

Avant campagne supervisée : `scripts/paper_supervised_precheck.py` ; après trades :
`scripts/report_trades_parquet.py <trades.parquet> --json`.

Rapport analyzers par fenêtre (transmis à chaque `run_mini_lab_week`) :
`--write-trades-analyzer-report [--trades-analyzer-names CSV]`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

backend_dir = Path(__file__).resolve().parent.parent

# Fenêtres calendaires (inclusives), labels stables pour dossiers `mini_week/<label>/`
# Données 1m disponibles (repo) : à partir de ~2025-06-02 (voir confirmation PHASE 1).
PRESETS: dict[str, List[Tuple[str, str, str]]] = {
    "nov2025": [
        ("2025-11-03", "2025-11-09", "202511_w01"),
        ("2025-11-10", "2025-11-16", "202511_w02"),
        ("2025-11-17", "2025-11-23", "202511_w03"),
        ("2025-11-24", "2025-11-30", "202511_w04"),
    ],
    "oct2025": [
        ("2025-10-06", "2025-10-12", "202510_w01"),
        ("2025-10-13", "2025-10-19", "202510_w02"),
        ("2025-10-20", "2025-10-26", "202510_w03"),
        ("2025-10-27", "2025-11-02", "202510_w04"),
    ],
    "sep2025": [
        ("2025-09-01", "2025-09-07", "202509_w01"),
        ("2025-09-08", "2025-09-14", "202509_w02"),
        ("2025-09-15", "2025-09-21", "202509_w03"),
        ("2025-09-22", "2025-09-28", "202509_w04"),
    ],
    "aug2025": [
        ("2025-08-04", "2025-08-10", "202508_w01"),
        ("2025-08-11", "2025-08-17", "202508_w02"),
        ("2025-08-18", "2025-08-24", "202508_w03"),
        ("2025-08-25", "2025-08-31", "202508_w04"),
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-labs multi-semaines (séquentiels)")
    parser.add_argument(
        "--preset",
        type=str,
        default="nov2025",
        choices=sorted(PRESETS.keys()),
        help="Jeu de fenêtres prédéfini",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Ignore une fenêtre si `mini_lab_summary_<label>.json` existe déjà",
    )
    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Ne pas exécuter `aggregate_mini_lab_summaries.py` à la fin",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="SPY,QQQ",
        help="Transmis à chaque `run_mini_lab_week.py`",
    )
    parser.add_argument(
        "--output-parent",
        type=str,
        default=None,
        help="Transmis à run_mini_lab_week : sorties sous mini_week/<output-parent>/<label>/ (ne pas écraser la baseline)",
    )
    parser.add_argument(
        "--playbooks-yaml",
        type=str,
        default=None,
        help="Chemin YAML dérivé (ex. sweep NF tp1) — transmis à chaque run_mini_lab_week",
    )
    parser.add_argument(
        "--nf-tp1-rr",
        type=float,
        default=None,
        help="Métadonnée PHASE B / arbitrage (summary uniquement) — transmis tel quel",
    )
    parser.add_argument(
        "--write-trades-analyzer-report",
        action="store_true",
        help="Transmis à run_mini_lab_week : mini_lab_trades_analyzer_report.json par fenêtre",
    )
    parser.add_argument(
        "--trades-analyzer-names",
        type=str,
        default="summary_r,exit_reason_mix,playbook_counts",
        help="Transmis avec --write-trades-analyzer-report (liste CSV)",
    )
    args = parser.parse_args()

    week_script = backend_dir / "scripts" / "run_mini_lab_week.py"
    agg_script = backend_dir / "scripts" / "aggregate_mini_lab_summaries.py"
    windows = PRESETS[args.preset]

    for start, end, label in windows:
        if args.output_parent:
            summary = (
                backend_dir
                / "results"
                / "labs"
                / "mini_week"
                / args.output_parent
                / label
                / f"mini_lab_summary_{label}.json"
            )
        else:
            summary = (
                backend_dir
                / "results"
                / "labs"
                / "mini_week"
                / label
                / f"mini_lab_summary_{label}.json"
            )
        if args.skip_existing and summary.is_file():
            print(f"[multiweek] skip existing {label}", flush=True)
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
        ]
        if args.output_parent:
            cmd.extend(["--output-parent", args.output_parent])
        if args.playbooks_yaml:
            yp = Path(args.playbooks_yaml)
            if not yp.is_absolute():
                yp = (backend_dir / yp).resolve()
            cmd.extend(["--playbooks-yaml", str(yp)])
        if args.nf_tp1_rr is not None:
            cmd.extend(["--nf-tp1-rr", str(args.nf_tp1_rr)])
        if args.write_trades_analyzer_report:
            cmd.append("--write-trades-analyzer-report")
            cmd.extend(["--trades-analyzer-names", args.trades_analyzer_names])
        print(f"[multiweek] RUN {label} {start}..{end}", flush=True)
        r = subprocess.run(cmd, cwd=str(backend_dir))
        if r.returncode != 0:
            print(f"[multiweek] FAIL {label} exit={r.returncode}", flush=True)
            return r.returncode

    if not args.no_aggregate and not args.output_parent:
        print("[multiweek] aggregate …", flush=True)
        r = subprocess.run(
            [sys.executable, str(agg_script), "--preset", args.preset],
            cwd=str(backend_dir),
        )
        if r.returncode != 0:
            return r.returncode
    elif args.output_parent and not args.no_aggregate:
        print(
            "[multiweek] skip aggregate_mini_lab_summaries (dédié baseline sans output-parent). "
            "Agrégateurs : aggregate_nf_1r_confirmation.py (nf1r_confirm_*), "
            "regen_nf_tp1_arbitration_artifacts.py (alias aggregate_nf_tp1_arbitration.py).",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
