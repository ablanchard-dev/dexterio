#!/usr/bin/env python3
"""Phase B0.2 — silent playbook funnel diagnosis.

Aggregates debug_counts_*.json from fair audits and classifies every playbook
that has zero trades across all 4 weeks into a 2-level taxonomy.

Level 1 (from debug_counts funnel):
  DETECTOR_NEVER_FIRES    : matches_total == 0
  SCORING_FILTERS_ALL     : matches > 0 but setups_created == 0
  RISK_FILTER_KILLS_ALL   : setups_created > 0 but after_risk == 0
  EXECUTION_LAYER_ISSUE   : after_risk > 0 but trades == 0

Level 2 (for DETECTOR_NEVER_FIRES only, read-only YAML parse):
  DISABLED_OR_WRONG_MODE  : enabled_in_modes missing AGGRESSIVE
  SESSION_WINDOW_MISMATCH : session != NY (or windows outside US hours)
  HTF_BIAS_GATE_REQUIRED  : htf_bias_allowed restricted (single bias only)
  TF_CONFIG_MISMATCH      : setup_tf / required_signals use non-standard TF
  PATTERN_PRECONDITION_BUG_OR_STRUCTURAL_RARITY : none of the above (manual review)

Usage:
  python backend/scripts/diagnose_silent_playbooks.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path


DEFAULT_LABELS = ["fair_jun_w3", "fair_aug_w3", "fair_oct_w2", "fair_nov_w4"]
PLAYBOOKS_YAML = backend_dir / "knowledge" / "playbooks.yml"


def _load_debug_counts(labels: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    root = Path(results_path("labs", "mini_week"))
    out = []
    for label in labels:
        for p in sorted((root / label).glob("debug_counts_*.json")):
            out.append((label, json.loads(p.read_text())))
    return out


def _load_trade_counts(labels: List[str]) -> Dict[str, int]:
    root = Path(results_path("labs", "mini_week"))
    counts: Dict[str, int] = {}
    for label in labels:
        for p in sorted((root / label).glob("trades_*.parquet")):
            df = pd.read_parquet(p, columns=["playbook"])
            for pb, n in df["playbook"].value_counts().items():
                counts[pb] = counts.get(pb, 0) + int(n)
    return counts


def _aggregate_funnel(debug_counts: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    agg: Dict[str, Dict[str, int]] = {}
    registered_union: set = set()
    for _, d in debug_counts:
        c = d.get("counts", {})
        for name in c.get("playbooks_registered_names", []):
            registered_union.add(name)
            agg.setdefault(name, {"matches": 0, "setups": 0, "after_risk": 0})
        for name, n in c.get("matches_by_playbook", {}).items():
            agg.setdefault(name, {"matches": 0, "setups": 0, "after_risk": 0})
            agg[name]["matches"] += int(n)
        for name, n in c.get("setups_created_by_playbook", {}).items():
            agg.setdefault(name, {"matches": 0, "setups": 0, "after_risk": 0})
            agg[name]["setups"] += int(n)
        for name, n in c.get("setups_after_risk_filter_by_playbook", {}).items():
            agg.setdefault(name, {"matches": 0, "setups": 0, "after_risk": 0})
            agg[name]["after_risk"] += int(n)
    for name in registered_union:
        agg.setdefault(name, {"matches": 0, "setups": 0, "after_risk": 0})
    return agg


def _classify_level1(matches: int, setups: int, after_risk: int, trades: int) -> str:
    if matches == 0:
        return "DETECTOR_NEVER_FIRES"
    if setups == 0:
        return "SCORING_FILTERS_ALL"
    if after_risk == 0:
        return "RISK_FILTER_KILLS_ALL"
    if trades == 0:
        return "EXECUTION_LAYER_ISSUE"
    return "NON_SILENT"


def _load_playbook_yaml() -> Dict[str, Dict[str, Any]]:
    with PLAYBOOKS_YAML.open("r") as f:
        docs = yaml.safe_load(f)
    by_name: Dict[str, Dict[str, Any]] = {}
    for pb in docs if isinstance(docs, list) else docs.get("playbooks", []):
        name = pb.get("playbook_name") or pb.get("id")
        if name:
            by_name[name] = pb
    return by_name


def _window_in_us_hours(time_windows: List[List[str]]) -> bool:
    """Check if any time_window overlaps 09:30-16:00 ET."""
    us_open_min = 9 * 60 + 30
    us_close_min = 16 * 60
    for win in time_windows or []:
        try:
            start_h, start_m = map(int, str(win[0]).split(":"))
            end_h, end_m = map(int, str(win[1]).split(":"))
            start = start_h * 60 + start_m
            end = end_h * 60 + end_m
            if start < us_close_min and end > us_open_min:
                return True
        except Exception:
            continue
    return False


def _classify_level2(pb_cfg: Dict[str, Any]) -> Tuple[str, str]:
    """Returns (level2_verdict, reason)."""
    modes = pb_cfg.get("enabled_in_modes") or []
    if "AGGRESSIVE" not in modes:
        return "DISABLED_OR_WRONG_MODE", f"enabled_in_modes={modes}"

    tf = pb_cfg.get("timefilters") or {}
    session = (tf.get("session") or "").upper()
    time_windows = tf.get("time_windows") or []
    if session and session not in ("NY", "ALL", ""):
        if not _window_in_us_hours(time_windows):
            return "SESSION_WINDOW_MISMATCH", f"session={session} time_windows={time_windows}"
    if time_windows and not _window_in_us_hours(time_windows):
        return "SESSION_WINDOW_MISMATCH", f"time_windows={time_windows} (no US overlap)"

    ctx = pb_cfg.get("context_requirements") or {}
    bias_allowed = ctx.get("htf_bias_allowed") or []
    if bias_allowed and len(bias_allowed) == 1 and bias_allowed[0] not in ("neutral", "any"):
        return "HTF_BIAS_GATE_REQUIRED", f"htf_bias_allowed={bias_allowed}"

    setup_tf = pb_cfg.get("setup_tf")
    if setup_tf and setup_tf not in ("1m", "5m", "15m", "30m", "1h"):
        return "TF_CONFIG_MISMATCH", f"setup_tf={setup_tf}"
    required = pb_cfg.get("required_signals") or []
    for sig in required:
        if "@" in str(sig):
            tf_part = str(sig).split("@", 1)[1]
            if tf_part not in ("1m", "5m", "15m", "30m", "1h"):
                return "TF_CONFIG_MISMATCH", f"required_signals={required}"

    return "PATTERN_PRECONDITION_BUG_OR_STRUCTURAL_RARITY", "passes config checks — detector code review needed"


def _render_markdown(silent_rows: List[Dict[str, Any]], nonsilent_rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# Phase B0.2 — Silent Playbook Funnel Diagnosis",
        "",
        "**Source:** debug_counts_*.json + trades_*.parquet from 4 fair audits (jun_w3 + aug_w3 + oct_w2 + nov_w4).",
        "",
        "## Silent playbooks (0 trades across 4 weeks)",
        "",
        "| playbook | matches_4w | setups_4w | after_risk_4w | trades_4w | level_1 | level_2 | reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in silent_rows:
        lines.append(
            f"| {r['playbook']} | {r['matches']} | {r['setups']} | {r['after_risk']} | {r['trades']} | "
            f"**{r['level_1']}** | {r.get('level_2', '-')} | {r.get('reason', '-')} |"
        )
    lines.append("")
    lines.append("## Non-silent playbooks (context)")
    lines.append("")
    lines.append("| playbook | matches_4w | setups_4w | after_risk_4w | trades_4w |")
    lines.append("|---|---|---|---|---|")
    for r in sorted(nonsilent_rows, key=lambda x: -x["trades"]):
        lines.append(
            f"| {r['playbook']} | {r['matches']} | {r['setups']} | {r['after_risk']} | {r['trades']} |"
        )
    lines.append("")
    lines.append("## Taxonomy")
    lines.append("- **Level 1** (funnel): DETECTOR_NEVER_FIRES / SCORING_FILTERS_ALL / RISK_FILTER_KILLS_ALL / EXECUTION_LAYER_ISSUE")
    lines.append("- **Level 2** (YAML config parse for DETECTOR_NEVER_FIRES):")
    lines.append("  - DISABLED_OR_WRONG_MODE — trivial fix (enable in AGGRESSIVE)")
    lines.append("  - SESSION_WINDOW_MISMATCH — config fix (time_windows don't overlap US hours)")
    lines.append("  - HTF_BIAS_GATE_REQUIRED — config fix (bias too strict)")
    lines.append("  - TF_CONFIG_MISMATCH — config fix (TF not loaded)")
    lines.append("  - PATTERN_PRECONDITION_BUG_OR_STRUCTURAL_RARITY — detector code review required (Phase C.0)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=str, default=",".join(DEFAULT_LABELS))
    ap.add_argument("--output-md", type=str, default=None)
    ap.add_argument("--output-json", type=str, default=None)
    args = ap.parse_args()

    labels = [s.strip() for s in args.labels.split(",") if s.strip()]

    dbg = _load_debug_counts(labels)
    if not dbg:
        print(f"No debug_counts for labels {labels}", file=sys.stderr)
        return 1

    funnel = _aggregate_funnel(dbg)
    trade_counts = _load_trade_counts(labels)
    yaml_map = _load_playbook_yaml()

    silent_rows = []
    nonsilent_rows = []
    for name, f in sorted(funnel.items()):
        trades = trade_counts.get(name, 0)
        row = {
            "playbook": name,
            "matches": f["matches"],
            "setups": f["setups"],
            "after_risk": f["after_risk"],
            "trades": trades,
        }
        if trades > 0:
            nonsilent_rows.append(row)
            continue
        level1 = _classify_level1(f["matches"], f["setups"], f["after_risk"], trades)
        row["level_1"] = level1
        if level1 == "DETECTOR_NEVER_FIRES":
            cfg = yaml_map.get(name)
            if cfg is None:
                row["level_2"] = "YAML_NOT_FOUND"
                row["reason"] = "playbook not found in playbooks.yml"
            else:
                lvl2, reason = _classify_level2(cfg)
                row["level_2"] = lvl2
                row["reason"] = reason
        else:
            row["level_2"] = "-"
            row["reason"] = "-"
        silent_rows.append(row)

    md = _render_markdown(silent_rows, nonsilent_rows)
    out_md = Path(args.output_md) if args.output_md else (
        backend_dir / "data" / "backtest_results" / "silent_playbooks_diagnosis.md"
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)

    out_json = Path(args.output_json) if args.output_json else (
        backend_dir / "data" / "backtest_results" / "silent_playbooks_diagnosis.json"
    )
    out_json.write_text(json.dumps({
        "labels": labels,
        "silent": silent_rows,
        "non_silent": nonsilent_rows,
    }, indent=2))

    print(md)
    print(f"\nWrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
