#!/usr/bin/env python3
"""
Audit 4 — filter splits.

Read-only. For each playbook, segments trades along several dimensions and
computes E[R] per bucket. Looks for dimensions where a subset has E[R]>0
with n≥15 (candidate filter for a future calib).

Dimensions explored (using only columns already in trade parquet):
  - minute of session entry (open 30min / mid / last 30min)
  - session_label
  - killzone_label
  - day of week
  - symbol (SPY vs QQQ)
  - direction (LONG vs SHORT)
  - mc_breakout_dir
  - SL distance quintiles (volatility proxy)
  - duration_minutes quintiles (a posteriori — diagnostic only)

For each dimension+playbook pair: output avg_R per bucket, n, and flag
buckets where (avg_R > 0) AND (n >= 15).
"""
from __future__ import annotations
import argparse
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_trades() -> pd.DataFrame:
    patterns = [
        "backend/results/labs/mini_week/survivor_v1/*/trades_*.parquet",
        "backend/results/labs/mini_week/fair_*/trades_*.parquet",
        "backend/results/labs/mini_week/aplus03_v2/*/trades_*.parquet",
        "backend/results/labs/mini_week/b_aplus04_v1/*/trades_*.parquet",
        "backend/results/labs/mini_week/r3_aplus03_tpcalib_v1/*/trades_*.parquet",
    ]
    dfs = []
    for pat in patterns:
        for f in glob.glob(str(REPO_ROOT / pat)):
            if "normalcaps" in f:
                continue
            try:
                df = pd.read_parquet(f)
                df["_source"] = Path(f).parent.parent.name
                dfs.append(df)
            except Exception:
                pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp_entry"] = pd.to_datetime(df["timestamp_entry"], utc=True)

    # Minute of session (US regular 13:30-20:00 UTC)
    df["hour_utc"] = df["timestamp_entry"].dt.hour
    df["min_of_day_utc"] = df["timestamp_entry"].dt.hour * 60 + df["timestamp_entry"].dt.minute
    # Session open = 13:30 UTC = 810
    open_mins = 13 * 60 + 30
    df["min_since_open"] = df["min_of_day_utc"] - open_mins
    # Buckets: 0-30 (first 30m), 30-120 (morning), 120-210 (midday/lunch), 210-330 (afternoon), 330+ (last 30)
    def bucket(m):
        if m < 0:
            return "pre_open"
        if m < 30:
            return "first_30m"
        if m < 120:
            return "morning_30_120"
        if m < 210:
            return "midday_120_210"
        if m < 330:
            return "afternoon_210_330"
        return "last_30m"
    df["session_bucket"] = df["min_since_open"].apply(bucket)

    # Day of week
    df["day_of_week"] = df["timestamp_entry"].dt.day_name()

    # SL distance % (vol proxy)
    df["sl_dist_pct"] = (
        abs(df["entry_price"] - df["stop_loss"]) / df["entry_price"] * 100
    )

    # Quintiles of SL distance
    try:
        df["sl_dist_quintile"] = pd.qcut(df["sl_dist_pct"], 5, labels=False, duplicates="drop")
    except Exception:
        df["sl_dist_quintile"] = -1

    return df


def split_by(df: pd.DataFrame, col: str, min_n: int = 15) -> list[dict]:
    out = []
    for val, sub in df.groupby(col, dropna=False):
        if len(sub) < 5:
            continue
        avg_r = float(sub["r_multiple"].mean())
        wr = float((sub["r_multiple"] > 0).mean()) * 100
        out.append({
            "bucket": str(val),
            "n": int(len(sub)),
            "avg_R": round(avg_r, 4),
            "winrate_pct": round(wr, 1),
            "flag_edge_candidate": bool(avg_r > 0 and len(sub) >= min_n),
        })
    return sorted(out, key=lambda r: -r["avg_R"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="backend/data/backtest_results/audit_filter_splits.json")
    ap.add_argument("--md-out", default="backend/data/backtest_results/audit_filter_splits.md")
    ap.add_argument("--min-pb-n", type=int, default=30)
    ap.add_argument("--min-bucket-n", type=int, default=15)
    args = ap.parse_args()

    df = load_trades()
    df = prepare(df)
    print(f"Total trades: {len(df)}, playbooks: {df['playbook'].nunique()}")

    DIMS = [
        "session_bucket",
        "session_label",
        "killzone_label",
        "day_of_week",
        "symbol",
        "direction",
        "mc_breakout_dir",
        "sl_dist_quintile",
    ]

    results = {}
    edge_candidates = []

    # Global splits first
    results["_GLOBAL_"] = {}
    for dim in DIMS:
        if dim not in df.columns:
            continue
        buckets = split_by(df, dim, min_n=args.min_bucket_n)
        results["_GLOBAL_"][dim] = buckets
        for b in buckets:
            if b["flag_edge_candidate"]:
                edge_candidates.append({
                    "playbook": "GLOBAL", "dim": dim,
                    "bucket": b["bucket"], "n": b["n"], "avg_R": b["avg_R"],
                    "wr": b["winrate_pct"],
                })

    # Per-playbook
    for pb in sorted(df["playbook"].unique()):
        sub = df[df["playbook"] == pb]
        if len(sub) < args.min_pb_n:
            continue
        results[pb] = {}
        for dim in DIMS:
            if dim not in sub.columns:
                continue
            buckets = split_by(sub, dim, min_n=args.min_bucket_n)
            results[pb][dim] = buckets
            for b in buckets:
                if b["flag_edge_candidate"]:
                    edge_candidates.append({
                        "playbook": pb, "dim": dim,
                        "bucket": b["bucket"], "n": b["n"], "avg_R": b["avg_R"],
                        "wr": b["winrate_pct"],
                    })

    out_path = REPO_ROOT / args.out
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"JSON: {out_path}")

    # MD
    md = [
        "# Audit 4 — filter splits",
        "",
        f"- Total trades: {len(df)}",
        f"- Playbooks analyzed: {len([k for k in results if k != '_GLOBAL_'])}",
        f"- Min bucket n for edge candidate: {args.min_bucket_n}",
        "",
        "## Edge candidates (avg_R > 0, n ≥ 15)",
        "",
    ]
    if not edge_candidates:
        md.append("**Aucun subset n'a avg_R > 0 avec n ≥ 15.**")
    else:
        md.extend([
            "| Playbook | Dimension | Bucket | n | avg_R | WR% |",
            "|---|---|---|---:|---:|---:|",
        ])
        for e in sorted(edge_candidates, key=lambda x: -x["avg_R"]):
            md.append(
                f"| {e['playbook']} | {e['dim']} | {e['bucket']} | {e['n']} | "
                f"{e['avg_R']:+.4f} | {e['wr']} |"
            )

    md.extend([
        "",
        "## Global splits (all playbooks merged)",
        "",
    ])
    for dim in DIMS:
        buckets = results["_GLOBAL_"].get(dim, [])
        if not buckets:
            continue
        md += [f"### {dim}", "", "| Bucket | n | avg_R | WR% | Edge? |", "|---|---:|---:|---:|---|"]
        for b in buckets:
            flag = "✅" if b["flag_edge_candidate"] else ""
            md.append(f"| {b['bucket']} | {b['n']} | {b['avg_R']:+.4f} | {b['winrate_pct']} | {flag} |")
        md.append("")

    md += [
        "## Lecture",
        "",
        "- **Edge candidate** = bucket où avg_R > 0 avec n ≥ 15. Signale une dimension qui isolerait potentiellement un subset trad.",
        "- Plus il y a de candidats sur la même dimension pour différents playbooks → dimension robuste.",
        "- **Attention** : les candidats découverts ici sont **in-sample** sur ce corpus 4-semaines. Appliquer tel quel sans test holdout = risque overfitting.",
        "- **Caveat MASTER** : les playbooks Aplus_XX ont déjà du require_close_above_trigger + entry_buffer_bps + structure_alignment. Ajouter un filtre de plus augmente les contraintes, réduit n, pas toujours souhaitable.",
        "",
    ]
    md_path = REPO_ROOT / args.md_out
    md_path.write_text("\n".join(md))
    print(f"MD: {md_path}")

    print(f"\nEdge candidates: {len(edge_candidates)}")
    for e in sorted(edge_candidates, key=lambda x: -x["avg_R"])[:10]:
        print(f"  {e['playbook']} / {e['dim']} / {e['bucket']}: n={e['n']}, avg_R={e['avg_R']:+.4f}, WR={e['wr']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
