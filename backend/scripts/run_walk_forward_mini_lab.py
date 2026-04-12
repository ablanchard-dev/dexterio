#!/usr/bin/env python3
"""
Enchaîne des `run_mini_lab_week.py` selon un plan walk-forward léger (2 OOS).

Sans modifier le moteur : sous-processus par fenêtre. Plan par défaut =
`walk_forward_two_splits_expanding` (même logique que `walk_forward_light.py`).

Usage (depuis backend/) :
  .venv/bin/python scripts/run_walk_forward_mini_lab.py \\
    --start 2025-08-01 --end 2025-11-30 --output-parent wf_aug_nov --dry-run

  # Puis sans dry-run ; arguments après -- sont relayés à run_mini_lab_week :
  .venv/bin/python scripts/run_walk_forward_mini_lab.py \\
    --start 2025-08-01 --end 2025-11-30 --output-parent wf_aug_nov \\
    -- --strict-manifest-coverage

  # Plan JSON produit par walk_forward_light.py :
  .venv/bin/python scripts/run_walk_forward_mini_lab.py \\
    --plan wf.json --output-parent wf_custom --include-train
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path  # noqa: E402
from utils.walk_forward_light import walk_forward_two_splits_expanding  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Walk-forward : enchaîne mini-lab par fenêtre")
    p.add_argument("--plan", type=str, default=None, help="JSON WalkForwardLightV0 (sinon --start/--end)")
    p.add_argument("--start", type=str, default=None)
    p.add_argument("--end", type=str, default=None)
    p.add_argument(
        "--output-parent",
        type=str,
        required=True,
        help="Sous-dossier labs/mini_week/<output-parent>/ (chaque label dans un sous-dossier)",
    )
    p.add_argument(
        "--label-prefix",
        type=str,
        default="wf",
        help="Labels = {prefix}_s{id}_{train|test}",
    )
    p.add_argument(
        "--include-train",
        action="store_true",
        help="Aussi lancer les fenêtres train (4 runs au lieu de 2)",
    )
    p.add_argument("--dry-run", action="store_true", help="Afficher les commandes sans exécuter")
    args, forwarded = p.parse_known_args()

    if args.plan:
        raw = Path(args.plan).read_text(encoding="utf-8")
        plan = json.loads(raw)
        if plan.get("schema_version") != "WalkForwardLightV0":
            print("WARN: schema_version attendu WalkForwardLightV0", file=sys.stderr)
    else:
        if not args.start or not args.end:
            print("ERROR: fournir --start et --end ou --plan", file=sys.stderr)
            return 2
        plan = walk_forward_two_splits_expanding(args.start, args.end)

    splits = plan.get("splits") or []
    if len(splits) < 1:
        print("ERROR: plan sans splits", file=sys.stderr)
        return 2

    runs: list[tuple[str, int, dict[str, str]]] = []
    for sp in splits:
        sid = int(sp["id"])
        if args.include_train:
            runs.append(("train", sid, sp["train"]))
        runs.append(("test", sid, sp["test"]))

    script = backend_dir / "scripts" / "run_mini_lab_week.py"
    py = sys.executable
    base_cmd = [py, str(script)]

    campaign_root = results_path("labs", "mini_week", args.output_parent)
    campaign_root.mkdir(parents=True, exist_ok=True)
    records = []
    exit_max = 0

    for phase, sid, win in runs:
        label = f"{args.label_prefix}_s{sid}_{phase}"
        cmd = [
            *base_cmd,
            "--start",
            win["start_date"],
            "--end",
            win["end_date"],
            "--label",
            label,
            "--output-parent",
            args.output_parent,
            *forwarded,
        ]
        line = " ".join(cmd)
        print(line, flush=True)
        records.append({"phase": phase, "split_id": sid, "window": win, "cmd": cmd})
        if args.dry_run:
            continue
        r = subprocess.run(cmd, cwd=str(backend_dir))
        exit_max = max(exit_max, r.returncode)

    meta = {
        "schema_version": "WalkForwardMiniLabCampaignV0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_parent": args.output_parent,
        "label_prefix": args.label_prefix,
        "include_train": args.include_train,
        "dry_run": args.dry_run,
        "forwarded_argv": forwarded,
        "plan": plan,
        "runs": records,
    }
    out_meta = campaign_root / "walk_forward_campaign.json"
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[wf_mini_lab] wrote {out_meta}", flush=True)

    return 0 if args.dry_run else exit_max


if __name__ == "__main__":
    raise SystemExit(main())
