#!/usr/bin/env python3
"""
Audit 1 — peak_R vs TP per-playbook.

Read-only. Loads existing trade parquets from 4-week corpora (fair audit,
survivor_v1, aplus03_v2, b_aplus04_v1, r3) and produces a per-playbook table:

  playbook | n | WR | E[R] | peak_R p50/p60/p80 | TP_RR median |
  ratio p80/TP | verdict

Verdict logic:
  - GEOMETRY_CONDEMNED    : peak_R p80 < TP_RR × 0.80 (TP rarely reachable)
  - GEOMETRY_TIGHT        : peak_R p80 in [TP × 0.80, TP × 1.10]
  - GEOMETRY_OK           : peak_R p80 > TP_RR × 1.10

This identifies playbooks where fixed-RR TP is structurally unreachable
(same pathology as Aplus_03 R.3 and Aplus_04 Option B).
"""
from __future__ import annotations
import argparse
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPORA = [
    ("fair", "backend/results/labs/mini_week/fair_*"),
    ("survivor_v1", "backend/results/labs/mini_week/survivor_v1/*"),
    ("aplus03_v2", "backend/results/labs/mini_week/aplus03_v2/*"),
    ("b_aplus04_v1", "backend/results/labs/mini_week/b_aplus04_v1/*"),
    ("r3_aplus03", "backend/results/labs/mini_week/r3_aplus03_tpcalib_v1/*"),
    ("calib_corpus_v1", "backend/results/labs/mini_week/calib_corpus_v1/*"),
    ("mass_s1_v1", "backend/results/labs/mini_week/mass_s1_v1/*"),
]


def load_corpus(pattern: str) -> pd.DataFrame:
    files = glob.glob(str(REPO_ROOT / pattern / "trades_*.parquet"))
    files = [f for f in files if "normalcaps" not in f]
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            df["_source_file"] = f
            dfs.append(df)
        except Exception as e:
            print(f"  warn: {f} — {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def compute_tp_rr(row) -> float:
    """TP1_RR from actual trade fields: (TP - entry) / (entry - SL) for LONGs."""
    entry = row.get("entry_price")
    sl = row.get("stop_loss")
    tp = row.get("take_profit_1")
    direction = str(row.get("direction", "")).upper()
    if entry is None or sl is None or tp is None:
        return float("nan")
    if direction in ("LONG", "BUY"):
        sl_dist = entry - sl
        tp_dist = tp - entry
    else:
        sl_dist = sl - entry
        tp_dist = entry - tp
    if sl_dist <= 0:
        return float("nan")
    return tp_dist / sl_dist


def summarize_playbook(df: pd.DataFrame, playbook: str, min_n: int = 15) -> dict | None:
    sub = df[df["playbook"] == playbook].copy()
    if len(sub) < min_n:
        return None

    sub["tp_rr"] = sub.apply(compute_tp_rr, axis=1)
    tp_rr_median = float(sub["tp_rr"].median())

    peak = sub["peak_r"].dropna()
    mae = sub["mae_r"].dropna()

    pR = {q: float(peak.quantile(q)) for q in [0.50, 0.60, 0.80, 0.90]}
    mR = {q: float(mae.quantile(q)) for q in [0.20, 0.50]}

    ratio = pR[0.80] / tp_rr_median if tp_rr_median > 0 else float("nan")

    # Verdict
    if ratio < 0.80:
        verdict = "GEOMETRY_CONDEMNED"
    elif ratio < 1.10:
        verdict = "GEOMETRY_TIGHT"
    else:
        verdict = "GEOMETRY_OK"

    # exit reasons
    exit_share = sub["exit_reason"].value_counts(normalize=True).to_dict()
    exit_share = {k: round(v * 100, 1) for k, v in exit_share.items()}

    return {
        "playbook": playbook,
        "n": int(len(sub)),
        "winrate": round(float((sub["r_multiple"] > 0).mean()) * 100, 1),
        "avg_R": round(float(sub["r_multiple"].mean()), 4),
        "peak_R_p50": round(pR[0.50], 3),
        "peak_R_p60": round(pR[0.60], 3),
        "peak_R_p80": round(pR[0.80], 3),
        "peak_R_p90": round(pR[0.90], 3),
        "mae_R_p20": round(mR[0.20], 3),
        "mae_R_p50": round(mR[0.50], 3),
        "tp_rr_median": round(tp_rr_median, 3),
        "ratio_p80_over_tp": round(ratio, 3) if not np.isnan(ratio) else None,
        "verdict": verdict,
        "sl_share_pct": exit_share.get("SL", 0),
        "tp1_share_pct": exit_share.get("TP1", 0),
        "time_stop_share_pct": exit_share.get("TIME_STOP", 0) + exit_share.get("MAX_DURATION", 0),
        "be_share_pct": exit_share.get("BREAKEVEN", 0),
        "eod_share_pct": exit_share.get("SESSION_END", 0) + exit_share.get("EOD", 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=15)
    ap.add_argument("--out", default="backend/data/backtest_results/audit_peakR_vs_TP.json")
    ap.add_argument("--md-out", default="backend/data/backtest_results/audit_peakR_vs_TP.md")
    args = ap.parse_args()

    per_corpus_summary = {}
    all_dfs = []

    for name, pattern in CORPORA:
        df = load_corpus(pattern)
        if df.empty:
            continue
        per_corpus_summary[name] = {
            "n_trades": int(len(df)),
            "n_playbooks": int(df["playbook"].nunique()),
        }
        df["_corpus"] = name
        all_dfs.append(df)

    merged = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    print(f"Total trades across corpora: {len(merged)}")
    print(f"Unique playbooks: {merged['playbook'].nunique()}")

    # For the main verdict, prefer survivor_v1 (caps actives) — most
    # representative of realistic conditions. Fall back to fair for playbooks
    # not covered by survivor_v1.
    results = {}

    # Primary: survivor_v1 (caps actives)
    for corpus_pref in ["survivor_v1", "fair", "aplus03_v2", "b_aplus04_v1",
                         "r3_aplus03", "calib_corpus_v1", "mass_s1_v1"]:
        sub = merged[merged["_corpus"] == corpus_pref]
        for pb in sorted(sub["playbook"].unique()):
            if pb in results:
                continue  # already covered by higher-priority corpus
            summary = summarize_playbook(sub, pb, min_n=args.min_n)
            if summary is not None:
                summary["source_corpus"] = corpus_pref
                results[pb] = summary

    table = sorted(results.values(), key=lambda r: (r["verdict"], -r["n"]))

    # Aggregate verdict counts
    verdict_counts = {}
    for r in table:
        verdict_counts[r["verdict"]] = verdict_counts.get(r["verdict"], 0) + 1

    out = {
        "min_n": args.min_n,
        "per_corpus": per_corpus_summary,
        "n_playbooks_analyzed": len(table),
        "verdict_counts": verdict_counts,
        "playbooks": table,
    }

    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"JSON: {out_path}")

    # Markdown table
    md_lines = [
        "# Audit 1 — peak_R vs TP per-playbook",
        "",
        f"- Min n per playbook: **{args.min_n}**",
        f"- Playbooks analyzed: **{len(table)}**",
        f"- Verdict distribution: {verdict_counts}",
        "",
        "## Table",
        "",
        "| Playbook | n | WR% | E[R] | peak_R p50/p60/p80 | mae_R p20/p50 | TP_RR | ratio p80/TP | Verdict | SL%/TP1%/TS% | Corpus |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for r in table:
        md_lines.append(
            f"| {r['playbook']} | {r['n']} | {r['winrate']} | {r['avg_R']:+.3f} | "
            f"{r['peak_R_p50']}/{r['peak_R_p60']}/{r['peak_R_p80']} | "
            f"{r['mae_R_p20']}/{r['mae_R_p50']} | "
            f"{r['tp_rr_median']} | "
            f"{r['ratio_p80_over_tp']} | "
            f"**{r['verdict']}** | "
            f"{r['sl_share_pct']}/{r['tp1_share_pct']}/{r['time_stop_share_pct']} | "
            f"{r['source_corpus']} |"
        )

    md_lines.extend([
        "",
        "## Lecture",
        "",
        "- **GEOMETRY_CONDEMNED** (ratio p80/TP < 0.80) : TP fixe > peak_R p80, le marché offre rarement assez de MFE pour atteindre le TP. Pathologie Aplus_03 R.3 / Aplus_04 Option B.",
        "- **GEOMETRY_TIGHT** (ratio 0.80–1.10) : TP atteignable mais rare. Winners plafonnent juste au-dessus.",
        "- **GEOMETRY_OK** (ratio > 1.10) : TP réaliste vs MFE observée.",
        "",
        "## Implication",
        "",
        "Pour tout playbook **GEOMETRY_CONDEMNED** :",
        "- fixed RR est structurellement mauvais → refaire le TP via `tp_logic: liquidity_draw` (Option A v2), OU abaisser TP_RR vers peak_R p60, OU KILL.",
        "- calibration incrémentale (bouger BE, trailing, max_duration) ne résoudra PAS le problème — on parle de géométrie TP, pas d'exit logic.",
        "",
    ])

    md_path = REPO_ROOT / args.md_out
    md_path.write_text("\n".join(md_lines))
    print(f"MD: {md_path}")

    print()
    print("Summary:")
    for v, c in verdict_counts.items():
        print(f"  {v}: {c}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
