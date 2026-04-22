#!/usr/bin/env python3
"""
Audit 2 — entry_confirm rejection funnel.

Read-only. Parses debug_counts JSON files from all 4-week runs and builds a
per-playbook funnel:

  matches → setups_created → after_risk_filter → trades_attempted → opened

Key metric: fraction of clean setups (post risk-filter) that die at
`entry_confirm_no_commit`. If high, entry_confirm is a structural killer of
potentially-good trades.

Also surfaces structure_alignment_stats (Aplus_03_v2) and any other gate
that appears in risk_rejects_by_playbook.
"""
from __future__ import annotations
import argparse
import glob
import json
from pathlib import Path
from collections import defaultdict


REPO_ROOT = Path(__file__).resolve().parents[2]

CORPORA = [
    "backend/results/labs/mini_week/fair_*",
    "backend/results/labs/mini_week/survivor_v1/*",
    "backend/results/labs/mini_week/aplus03_v2/*",
    "backend/results/labs/mini_week/b_aplus04_v1/*",
    "backend/results/labs/mini_week/r3_aplus03_tpcalib_v1/*",
    "backend/results/labs/mini_week/calib_corpus_v1/*",
]


def find_debug_files() -> list[Path]:
    out = []
    for pat in CORPORA:
        files = glob.glob(str(REPO_ROOT / pat / "debug_counts*.json"))
        out.extend(Path(f) for f in files if "normalcaps" not in f)
    return out


def load_counts(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def analyze_file(path: Path) -> dict:
    data = load_counts(path)
    c = data.get("counts", {})
    sa = data.get("structure_alignment_stats", {}) or {}
    tp = data.get("tp_reason_stats", {}) or {}
    run_id = data.get("run_id", path.stem)

    matches_by_pb = c.get("matches_by_playbook", {}) or {}
    setups_created_by_pb = c.get("setups_created_by_playbook", {}) or {}
    after_risk_by_pb = c.get("setups_after_risk_filter_by_playbook", {}) or {}
    trades_opened_by_pb = c.get("trades_opened_by_playbook", {}) or {}
    trades_attempted_by_pb = c.get("trades_attempted_by_playbook", {}) or {}

    rej_reason_total = c.get("trades_open_rejected_by_reason", {}) or {}
    # The rejection reason at the engine level is not split by playbook in
    # counts, but we can attribute at aggregate level. We attribute
    # entry_confirm_no_commit proportionally to attempted trades per playbook.
    total_attempted = sum(trades_attempted_by_pb.values()) if trades_attempted_by_pb else 0
    total_opened = sum(trades_opened_by_pb.values()) if trades_opened_by_pb else 0
    total_rej_entry_confirm = rej_reason_total.get("entry_confirm_no_commit", 0)

    pb_rows = []
    all_pbs = set(matches_by_pb) | set(setups_created_by_pb) | set(after_risk_by_pb) | set(trades_opened_by_pb)
    for pb in sorted(all_pbs):
        matches = matches_by_pb.get(pb, 0)
        setups_created = setups_created_by_pb.get(pb, 0)
        after_risk = after_risk_by_pb.get(pb, 0)
        opened = trades_opened_by_pb.get(pb, 0)
        attempted = trades_attempted_by_pb.get(pb, 0) or after_risk
        # Proportional attribution of entry_confirm_no_commit rejections
        if total_attempted > 0 and attempted > 0:
            entry_confirm_rej_est = round(total_rej_entry_confirm * attempted / total_attempted, 1)
        else:
            entry_confirm_rej_est = 0
        pb_rows.append({
            "playbook": pb,
            "matches": matches,
            "setups_created": setups_created,
            "after_risk_filter": after_risk,
            "trades_attempted": attempted,
            "trades_opened": opened,
            "entry_confirm_rej_est": entry_confirm_rej_est,
            "structure_alignment_stats": sa.get(pb),
            "tp_reason": tp.get(pb),
        })

    return {
        "run_id": run_id,
        "file": str(path),
        "total_attempted": total_attempted,
        "total_opened": total_opened,
        "total_rej_entry_confirm": total_rej_entry_confirm,
        "playbooks": pb_rows,
    }


def aggregate_across_files(per_file: list[dict]) -> dict:
    """Aggregate across weeks/runs by playbook."""
    agg: dict[str, dict] = defaultdict(lambda: {
        "matches": 0, "setups_created": 0, "after_risk_filter": 0,
        "trades_attempted": 0, "trades_opened": 0, "entry_confirm_rej_est": 0,
        "sa_evaluated": 0, "sa_rejected": 0, "sa_pass_aligned": 0,
        "tp_reason_counts": defaultdict(int),
        "runs": 0,
    })
    for fr in per_file:
        for pb_row in fr["playbooks"]:
            pb = pb_row["playbook"]
            a = agg[pb]
            a["matches"] += pb_row["matches"]
            a["setups_created"] += pb_row["setups_created"]
            a["after_risk_filter"] += pb_row["after_risk_filter"]
            a["trades_attempted"] += pb_row["trades_attempted"]
            a["trades_opened"] += pb_row["trades_opened"]
            a["entry_confirm_rej_est"] += pb_row["entry_confirm_rej_est"]
            a["runs"] += 1
            sa = pb_row.get("structure_alignment_stats")
            if sa:
                a["sa_evaluated"] += sa.get("evaluated", 0)
                a["sa_rejected"] += sa.get("rejected", 0)
                a["sa_pass_aligned"] += sa.get("pass_aligned", 0)
            tp = pb_row.get("tp_reason") or {}
            for reason, cnt in tp.items():
                a["tp_reason_counts"][reason] += cnt

    # Compute ratios
    out_rows = []
    for pb, a in agg.items():
        attempted = a["trades_attempted"] or 0
        opened = a["trades_opened"] or 0
        ec_rej = a["entry_confirm_rej_est"] or 0
        ec_kill_rate = (ec_rej / attempted * 100) if attempted > 0 else 0
        open_rate = (opened / attempted * 100) if attempted > 0 else 0
        match_to_open = (opened / a["matches"] * 100) if a["matches"] > 0 else 0
        sa_reject_rate = (a["sa_rejected"] / a["sa_evaluated"] * 100) if a["sa_evaluated"] > 0 else None
        tp_stats = dict(a["tp_reason_counts"])
        out_rows.append({
            "playbook": pb,
            "matches": a["matches"],
            "setups_created": a["setups_created"],
            "after_risk_filter": a["after_risk_filter"],
            "trades_attempted": attempted,
            "trades_opened": opened,
            "entry_confirm_rej_est": round(ec_rej, 1),
            "entry_confirm_kill_rate_pct": round(ec_kill_rate, 1),
            "open_rate_from_attempt_pct": round(open_rate, 1),
            "match_to_open_pct": round(match_to_open, 3),
            "sa_evaluated": a["sa_evaluated"],
            "sa_rejected": a["sa_rejected"],
            "sa_reject_rate_pct": round(sa_reject_rate, 1) if sa_reject_rate is not None else None,
            "tp_reason_counts": tp_stats,
        })
    return out_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-attempts", type=int, default=10)
    ap.add_argument("--out", default="backend/data/backtest_results/audit_entry_confirm.json")
    ap.add_argument("--md-out", default="backend/data/backtest_results/audit_entry_confirm.md")
    args = ap.parse_args()

    files = find_debug_files()
    print(f"Found {len(files)} debug_counts files")

    per_file = [analyze_file(f) for f in files]
    rows = aggregate_across_files(per_file)

    rows = [r for r in rows if r["trades_attempted"] >= args.min_attempts]
    rows.sort(key=lambda r: -r["entry_confirm_kill_rate_pct"])

    out = {
        "n_files": len(files),
        "min_attempts": args.min_attempts,
        "playbooks": rows,
    }
    out_path = REPO_ROOT / args.out
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"JSON: {out_path}")

    md = [
        "# Audit 2 — entry_confirm rejection funnel",
        "",
        f"- Corpora: {len(files)} debug_counts files (fair + survivor_v1 + Option A/B + R.3 + calib_corpus_v1)",
        f"- Min trades attempted per playbook: **{args.min_attempts}**",
        "",
        "## Funnel table",
        "",
        "| Playbook | Matches | SetupsCreated | AfterRisk | Attempted | Opened | EntryConfirmRejEst | EC kill% | OpenRate% | Match→Open% | SA rej% | tp_reason breakdown |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        tp_str = ", ".join(f"{k}:{v}" for k, v in list(r["tp_reason_counts"].items())[:3])
        md.append(
            f"| {r['playbook']} | {r['matches']} | {r['setups_created']} | {r['after_risk_filter']} "
            f"| {r['trades_attempted']} | {r['trades_opened']} | {r['entry_confirm_rej_est']} "
            f"| **{r['entry_confirm_kill_rate_pct']}** | {r['open_rate_from_attempt_pct']} "
            f"| {r['match_to_open_pct']} | {r['sa_reject_rate_pct']} "
            f"| {tp_str} |"
        )

    md.extend([
        "",
        "## Lecture",
        "",
        "- **EC kill%** = estimation proportionnelle du % de trades attempts tués par `entry_confirm_no_commit` (l'engine agrège cette stat globalement, pas par playbook ; attribution proportionnelle aux attempts).",
        "- **Match→Open%** = efficience bout-en-bout : combien de matches du détecteur deviennent des trades réels.",
        "- **SA rej%** = structure_alignment gate rejection (Aplus_03_v2 uniquement pour l'instant).",
        "",
        "## Implications",
        "",
        "Si **EC kill% > 40%** : entry_confirm filtre la moitié des setups clean. Soit le gate est trop strict, soit le signal ne confirme jamais proprement en fin de 5m.",
        "Si **Match→Open% < 0.5%** : compression énorme entre détection et exécution — normale si le playbook est spécifique (Aplus_03_v2 : 40 matches → 8 après SA → 2 opened = 5% → 0.05% end-to-end).",
        "",
    ])
    md_path = REPO_ROOT / args.md_out
    md_path.write_text("\n".join(md))
    print(f"MD: {md_path}")

    # Summary
    high_ec = [r for r in rows if r["entry_confirm_kill_rate_pct"] > 40]
    print(f"\nPlaybooks with EC kill% > 40%: {len(high_ec)}")
    for r in high_ec:
        print(f"  {r['playbook']}: attempted={r['trades_attempted']}, EC kill%={r['entry_confirm_kill_rate_pct']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
