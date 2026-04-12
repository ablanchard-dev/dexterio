#!/usr/bin/env python3
"""
Lit les `debug_counts_miniweek_*.json` sous `results/labs/mini_week/*/`
et produit un tableau consolidé (JSON + markdown doc).

Usage (depuis backend/) :
  .venv/bin/python scripts/aggregate_mini_lab_summaries.py --preset nov2025
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.mini_lab_funnel_playbooks import MINI_LAB_FUNNEL_PLAYBOOKS  # noqa: E402

RESULTS_MINI = backend_dir / "results" / "labs" / "mini_week"

# Même ordre que `run_mini_lab_multiweek.PRESETS` pour tri stable
PRESET_LABEL_ORDER: Dict[str, List[str]] = {
    "nov2025": ["202511_w01", "202511_w02", "202511_w03", "202511_w04"],
}


def _funnel_from_counts(counts: Dict[str, Any], pb: str) -> Dict[str, int]:
    return {
        "M": int(counts.get("matches_by_playbook", {}).get(pb, 0)),
        "S": int(counts.get("setups_created_by_playbook", {}).get(pb, 0)),
        "SR": int(counts.get("setups_after_risk_filter_by_playbook", {}).get(pb, 0)),
        "T": int(counts.get("trades_opened_by_playbook", {}).get(pb, 0)),
    }


def _load_debug_file(path: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("counts") or {}, data.get("config") or {}


def _discover_labels(preset: str) -> List[str]:
    if preset in PRESET_LABEL_ORDER:
        return PRESET_LABEL_ORDER[preset]
    # fallback : tous les sous-dossiers `202511_w*`
    if not RESULTS_MINI.is_dir():
        return []
    out: List[str] = []
    for p in sorted(RESULTS_MINI.iterdir()):
        if p.is_dir() and re.match(r"^202511_w\d\d$", p.name):
            out.append(p.name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", type=str, default="nov2025")
    args = parser.parse_args()

    labels = _discover_labels(args.preset)
    if not labels:
        print("No mini_week windows found.", file=sys.stderr)
        return 1

    rows: List[Dict[str, Any]] = []
    for label in labels:
        dc_path = RESULTS_MINI / label / f"debug_counts_miniweek_{label}.json"
        if not dc_path.is_file():
            print(f"WARN: missing {dc_path}", file=sys.stderr)
            continue
        counts, cfg = _load_debug_file(dc_path)
        row: Dict[str, Any] = {
            "label": label,
            "start_date": cfg.get("start_date"),
            "end_date": cfg.get("end_date"),
            "total_trades": int(counts.get("trades_opened_total", 0)),
            "playbooks": {},
        }
        for pb in MINI_LAB_FUNNEL_PLAYBOOKS:
            row["playbooks"][pb] = _funnel_from_counts(counts, pb)
        rows.append(row)

    consolidated = {
        "preset": args.preset,
        "source": "debug_counts_miniweek_*.json",
        "windows": rows,
    }
    out_json = RESULTS_MINI / f"consolidated_mini_week_{args.preset}.json"
    out_json.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    print(f"wrote {out_json}", flush=True)

    # Markdown pour `backend/docs/`
    lines: List[str] = [
        f"# Multi-week validation — preset `{args.preset}`",
        "",
        "**Source de vérité :** `results/labs/mini_week/consolidated_mini_week_{}.json`".format(
            args.preset
        ),
        "",
        "Funnel par fenêtre : **M** = matches, **S** = setups créés, **SR** = après risk, **T** = trades.",
        "",
    ]
    for pb in MINI_LAB_FUNNEL_PLAYBOOKS:
        lines.append(f"## {pb}")
        lines.append("")
        lines.append("| Fenêtre | Dates | M | S | SR | T | Total trades run |")
        lines.append("|---------|-------|--:|--:|---:|--:|------------------:|")
        for r in rows:
            f = r["playbooks"][pb]
            lines.append(
                f"| `{r['label']}` | {r.get('start_date')} → {r.get('end_date')} | "
                f"{f['M']} | {f['S']} | {f['SR']} | {f['T']} | {r['total_trades']} |"
            )
        lines.append("")

    doc_path = backend_dir / "docs" / f"MULTI_WEEK_VALIDATION_{args.preset.upper()}.md"
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {doc_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
