#!/usr/bin/env python3
"""
Phase -1: Validity Report Analyzer

Reads validity_report_<run_id>.jsonl produced by BacktestEngine
and outputs a structured diagnostic of pipeline validity.

Usage:
    python -m scripts.analyze_validity_report <path_to_validity_report.jsonl>
    python -m scripts.analyze_validity_report results/labs/mini_week/*/validity_report_*.jsonl
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime


def load_records(path: str) -> list:
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def analyze(records: list) -> dict:
    if not records:
        return {"error": "No records found"}

    # --- Per-playbook aggregation ---
    by_playbook = defaultdict(lambda: {
        "total_setups": 0,
        "trades_generated": 0,
        "fallback_tf_count": 0,
        "aggressive_bypass_count": 0,
        "scores": [],
        "grades": defaultdict(int),
        "placeholder_weight_pcts": [],
        "semi_placeholder_weight_pcts": [],
        "real_weight_pcts": [],
        "component_values": defaultdict(list),
        "component_types": {},
        "pattern_tfs": defaultdict(int),
        "setup_tf_requested": None,
        "trade_outcomes": defaultdict(int),
        "pnl_net_Rs": [],
        "bypasses": defaultdict(int),
        "timestamps": [],
    })

    for rec in records:
        pb = rec.get("playbook", "UNKNOWN")
        d = by_playbook[pb]
        d["total_setups"] += 1
        d["setup_tf_requested"] = rec.get("setup_tf_requested")

        if rec.get("trade_generated"):
            d["trades_generated"] += 1
        if rec.get("fallback_tf_used"):
            d["fallback_tf_count"] += 1
        if rec.get("aggressive_bypass_used"):
            d["aggressive_bypass_count"] += 1

        score = rec.get("score_total", 0.0)
        d["scores"].append(score)

        grade = rec.get("grade", "?")
        d["grades"][grade] += 1

        d["placeholder_weight_pcts"].append(rec.get("placeholder_weight_pct", 0.0))
        d["semi_placeholder_weight_pcts"].append(rec.get("semi_placeholder_weight_pct", 0.0))
        d["real_weight_pcts"].append(rec.get("real_weight_pct", 0.0))

        # Component breakdown
        comps = rec.get("component_scores", {})
        for cname, cinfo in comps.items():
            if isinstance(cinfo, dict):
                d["component_values"][cname].append(cinfo.get("value", 0.0))
                d["component_types"][cname] = cinfo.get("type", "unknown")
            else:
                d["component_values"][cname].append(cinfo)

        # Pattern TFs
        for tf in rec.get("pattern_tfs_used", []):
            d["pattern_tfs"][tf] += 1

        # Trade outcomes
        outcome = rec.get("trade_outcome")
        if outcome:
            d["trade_outcomes"][outcome] += 1
            pnl = rec.get("pnl_net_R")
            if pnl is not None:
                d["pnl_net_Rs"].append(pnl)

        # Bypasses detail
        for bp in rec.get("bypasses_list", []):
            d["bypasses"][bp] += 1

        # Timestamps for daily rate
        d["timestamps"].append(rec.get("timestamp", ""))

    # --- Compute summary stats ---
    report = {
        "total_records": len(records),
        "playbooks": {},
    }

    for pb, d in by_playbook.items():
        scores = d["scores"]
        n = len(scores)

        # Daily rates
        unique_days = set()
        for ts in d["timestamps"]:
            try:
                unique_days.add(ts[:10])
            except Exception:
                pass
        n_days = max(len(unique_days), 1)

        # Score stats
        scores_sorted = sorted(scores)
        mean_score = sum(scores) / n if n else 0
        std_score = (sum((s - mean_score) ** 2 for s in scores) / n) ** 0.5 if n > 1 else 0

        # Component stats
        component_summary = {}
        for cname, vals in d["component_values"].items():
            if vals:
                ctype = d["component_types"].get(cname, "unknown")
                cmean = sum(vals) / len(vals)
                cstd = (sum((v - cmean) ** 2 for v in vals) / len(vals)) ** 0.5 if len(vals) > 1 else 0
                unique_vals = len(set(round(v, 6) for v in vals))
                component_summary[cname] = {
                    "type": ctype,
                    "mean": round(cmean, 4),
                    "std": round(cstd, 4),
                    "min": round(min(vals), 4),
                    "max": round(max(vals), 4),
                    "unique_values": unique_vals,
                    "is_constant": unique_vals <= 2,
                    "count": len(vals),
                }

        # Phantom setups: setups where 100% of score comes from placeholders
        phantom_count = sum(1 for p in d["placeholder_weight_pcts"] if p >= 0.99)

        pb_report = {
            "total_setups": n,
            "trades_generated": d["trades_generated"],
            "trade_rate_pct": round(d["trades_generated"] / n * 100, 1) if n else 0,
            "setups_per_day": round(n / n_days, 1),
            "trades_per_day": round(d["trades_generated"] / n_days, 1),
            "n_days": n_days,
            "setup_tf_requested": d["setup_tf_requested"],
            "pattern_tfs_distribution": dict(d["pattern_tfs"]),
            "fallback_tf": {
                "count": d["fallback_tf_count"],
                "pct": round(d["fallback_tf_count"] / n * 100, 1) if n else 0,
            },
            "aggressive_bypass": {
                "count": d["aggressive_bypass_count"],
                "pct": round(d["aggressive_bypass_count"] / n * 100, 1) if n else 0,
                "details": dict(d["bypasses"]),
            },
            "scoring": {
                "mean": round(mean_score, 4),
                "std": round(std_score, 4),
                "min": round(scores_sorted[0], 4) if scores_sorted else 0,
                "max": round(scores_sorted[-1], 4) if scores_sorted else 0,
                "p25": round(scores_sorted[int(n * 0.25)], 4) if n >= 4 else None,
                "p50": round(scores_sorted[int(n * 0.50)], 4) if n >= 2 else None,
                "p75": round(scores_sorted[int(n * 0.75)], 4) if n >= 4 else None,
            },
            "grade_distribution": dict(d["grades"]),
            "placeholder_weight_pct": {
                "mean": round(sum(d["placeholder_weight_pcts"]) / n, 4) if n else 0,
                "max": round(max(d["placeholder_weight_pcts"]), 4) if d["placeholder_weight_pcts"] else 0,
            },
            "semi_placeholder_weight_pct": {
                "mean": round(sum(d["semi_placeholder_weight_pcts"]) / n, 4) if n else 0,
            },
            "real_weight_pct": {
                "mean": round(sum(d["real_weight_pcts"]) / n, 4) if n else 0,
            },
            "phantom_setups": {
                "count": phantom_count,
                "pct": round(phantom_count / n * 100, 1) if n else 0,
            },
            "component_breakdown": component_summary,
            "trade_outcomes": dict(d["trade_outcomes"]),
            "pnl_net_R": {
                "mean": round(sum(d["pnl_net_Rs"]) / len(d["pnl_net_Rs"]), 4) if d["pnl_net_Rs"] else None,
                "total": round(sum(d["pnl_net_Rs"]), 4) if d["pnl_net_Rs"] else None,
                "count": len(d["pnl_net_Rs"]),
            },
        }
        report["playbooks"][pb] = pb_report

    # --- Global summary ---
    all_fallback = sum(d["fallback_tf_count"] for d in by_playbook.values())
    all_bypass = sum(d["aggressive_bypass_count"] for d in by_playbook.values())
    all_total = sum(d["total_setups"] for d in by_playbook.values())
    all_trades = sum(d["trades_generated"] for d in by_playbook.values())
    all_placeholder_pcts = []
    for d in by_playbook.values():
        all_placeholder_pcts.extend(d["placeholder_weight_pcts"])

    report["global_summary"] = {
        "total_setups": all_total,
        "total_trades": all_trades,
        "pct_fallback_tf": round(all_fallback / all_total * 100, 1) if all_total else 0,
        "pct_aggressive_bypass": round(all_bypass / all_total * 100, 1) if all_total else 0,
        "mean_placeholder_weight_pct": round(sum(all_placeholder_pcts) / len(all_placeholder_pcts), 4) if all_placeholder_pcts else 0,
    }

    return report


def print_report(report: dict):
    print("=" * 80)
    print("VALIDITY REPORT ANALYSIS — Phase -1 Instrumentation")
    print("=" * 80)

    gs = report.get("global_summary", {})
    print(f"\nTotal records: {report['total_records']}")
    print(f"Total setups evaluated: {gs.get('total_setups', 0)}")
    print(f"Total trades generated: {gs.get('total_trades', 0)}")
    print(f"% setups with TF fallback: {gs.get('pct_fallback_tf', 0)}%")
    print(f"% setups with AGGRESSIVE bypass: {gs.get('pct_aggressive_bypass', 0)}%")
    print(f"Mean placeholder weight in score: {gs.get('mean_placeholder_weight_pct', 0) * 100:.1f}%")

    for pb_name, pb in report.get("playbooks", {}).items():
        print(f"\n{'─' * 80}")
        print(f"PLAYBOOK: {pb_name}")
        print(f"  setup_tf requested: {pb['setup_tf_requested']}")
        print(f"  Setups: {pb['total_setups']} | Trades: {pb['trades_generated']} ({pb['trade_rate_pct']}%)")
        print(f"  Setups/day: {pb['setups_per_day']} | Trades/day: {pb['trades_per_day']} ({pb['n_days']} days)")

        print(f"  TF fallback: {pb['fallback_tf']['count']} ({pb['fallback_tf']['pct']}%)")
        print(f"  AGGRESSIVE bypass: {pb['aggressive_bypass']['count']} ({pb['aggressive_bypass']['pct']}%)")
        if pb['aggressive_bypass']['details']:
            for bp, cnt in pb['aggressive_bypass']['details'].items():
                print(f"    - {bp}: {cnt}")

        print(f"  Pattern TFs used: {pb['pattern_tfs_distribution']}")

        sc = pb['scoring']
        print(f"  Score: mean={sc['mean']:.4f} std={sc['std']:.4f} [{sc['min']:.4f} .. {sc['max']:.4f}]")
        if sc['p25'] is not None:
            print(f"         p25={sc['p25']:.4f} p50={sc['p50']:.4f} p75={sc['p75']:.4f}")

        print(f"  Grades: {pb['grade_distribution']}")
        print(f"  Placeholder weight: mean={pb['placeholder_weight_pct']['mean']*100:.1f}% max={pb['placeholder_weight_pct']['max']*100:.1f}%")
        print(f"  Real weight: mean={pb['real_weight_pct']['mean']*100:.1f}%")
        print(f"  Phantom setups (100% placeholder): {pb['phantom_setups']['count']} ({pb['phantom_setups']['pct']}%)")

        print(f"  Component breakdown:")
        for cname, cs in sorted(pb['component_breakdown'].items()):
            marker = " **CONSTANT**" if cs['is_constant'] else ""
            print(f"    [{cs['type']:>16s}] {cname:>20s}: mean={cs['mean']:.4f} std={cs['std']:.4f} unique={cs['unique_values']}{marker}")

        if pb['pnl_net_R']['count'] > 0:
            print(f"  Trade outcomes: {pb['trade_outcomes']}")
            print(f"  PnL net R: mean={pb['pnl_net_R']['mean']:.4f} total={pb['pnl_net_R']['total']:.4f} ({pb['pnl_net_R']['count']} trades)")

    print(f"\n{'=' * 80}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.analyze_validity_report <validity_report.jsonl> [...]")
        sys.exit(1)

    all_records = []
    for path_str in sys.argv[1:]:
        for p in sorted(Path(".").glob(path_str)) if "*" in path_str else [Path(path_str)]:
            if p.exists():
                recs = load_records(str(p))
                print(f"Loaded {len(recs)} records from {p}")
                all_records.extend(recs)
            else:
                print(f"WARNING: {p} does not exist, skipping")

    if not all_records:
        print("No records loaded. Exiting.")
        sys.exit(1)

    report = analyze(all_records)

    # Save JSON report
    out_path = Path(sys.argv[1]).parent / "validity_analysis.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nJSON report saved to: {out_path}")

    # Print human-readable report
    print_report(report)


if __name__ == "__main__":
    main()
