#!/usr/bin/env python3
"""Phase A.3 — classify playbooks from a fair audit.

Reads trades parquet(s) from a fair audit (one or several weeks),
computes per-playbook metrics incl. MAE/MFE, classifies each playbook
into KILL / CALIBRATE / QUARANTINE, and writes a VERDICT.md report.

Usage:
  python scripts/analyze_fair_audit.py \
    --inputs results/labs/mini_week/fair_oct_w2 [more dirs...] \
    --output results/labs/mini_week/VERDICT_fair_audit.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pandas as pd


CLASSIFY_RULES = """
Classification rules (Phase A.3):
  - KILL        : trades >= 15 AND E[R] < -0.1  (proven destructor)
  - CALIBRATE   : trades >= 15 AND -0.1 <= E[R] <= 0.15 AND avg(|mae_r|) > 0.3
                  (signal triggers often, losses contained, TP/SL likely miscalibrated)
  - PROMOTE     : trades >= 15 AND E[R] > 0.15  (already edge-positive)
  - QUARANTINE  : otherwise  (too few trades OR inconclusive)
"""


def load_trades_parquet(paths: List[Path]) -> pd.DataFrame:
    frames = []
    for d in paths:
        hits = list(d.rglob("trades_*.parquet"))
        for p in hits:
            try:
                frames.append(pd.read_parquet(p))
            except Exception as e:
                print(f"WARN: could not read {p}: {e}", file=sys.stderr)
    if not frames:
        raise SystemExit(f"No trades parquet found under {paths}")
    df = pd.concat(frames, ignore_index=True)
    return df


def classify_row(r: pd.Series) -> str:
    n = int(r["trades"])
    e = float(r["expectancy_r"])
    mae_abs = abs(float(r["avg_mae_r"]))
    if n < 15:
        return "QUARANTINE"
    if e < -0.1:
        return "KILL"
    if e > 0.15:
        return "PROMOTE"
    if mae_abs > 0.3:
        return "CALIBRATE"
    return "QUARANTINE"


def per_playbook_stats(df: pd.DataFrame) -> pd.DataFrame:
    has_mae = "mae_r" in df.columns
    has_peak = "peak_r" in df.columns
    rows = []
    for pb, g in df.groupby("playbook"):
        r = pd.to_numeric(g["r_multiple"], errors="coerce")
        dur = pd.to_numeric(g.get("duration_minutes", pd.Series(dtype=float)), errors="coerce")
        mae = pd.to_numeric(g.get("mae_r", pd.Series(dtype=float)), errors="coerce") if has_mae else pd.Series([0.0] * len(g))
        peak = pd.to_numeric(g.get("peak_r", pd.Series(dtype=float)), errors="coerce") if has_peak else pd.Series([0.0] * len(g))
        exits = g.get("exit_reason", pd.Series(dtype=str))
        total = int(len(g))
        wins = int((r > 0).sum())
        losses = int((r < 0).sum())
        total_r = float(r.sum(skipna=True))
        exp_r = float(r.mean(skipna=True)) if total > 0 else 0.0
        wr = 100.0 * wins / total if total else 0.0
        exit_top = exits.value_counts().head(3).to_dict()
        exit_str = ", ".join(f"{k}:{v}" for k, v in exit_top.items())
        rows.append({
            "playbook": pb,
            "trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": round(wr, 1),
            "total_r": round(total_r, 3),
            "expectancy_r": round(exp_r, 4),
            "avg_mae_r": round(float(mae.mean(skipna=True)) if len(mae) else 0.0, 3),
            "min_mae_r": round(float(mae.min(skipna=True)) if len(mae) else 0.0, 3),
            "avg_peak_r": round(float(peak.mean(skipna=True)) if len(peak) else 0.0, 3),
            "p50_duration": round(float(dur.median(skipna=True)) if len(dur) else 0.0, 1),
            "exit_mix": exit_str,
        })
    out = pd.DataFrame(rows).sort_values("expectancy_r", ascending=False).reset_index(drop=True)
    out["verdict"] = out.apply(classify_row, axis=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="Directories containing trades_*.parquet")
    ap.add_argument("--output", type=str, default=None, help="Markdown output path")
    args = ap.parse_args()

    input_paths = [Path(p).expanduser().resolve() for p in args.inputs]
    df = load_trades_parquet(input_paths)
    stats = per_playbook_stats(df)

    total_trades = int(len(df))
    portfolio_r = float(pd.to_numeric(df["r_multiple"], errors="coerce").sum(skipna=True))
    portfolio_e = portfolio_r / total_trades if total_trades else 0.0

    verdict_counts = stats["verdict"].value_counts().to_dict()

    report = []
    report.append("# Phase A.3 — Fair Audit Verdict\n")
    report.append(f"**Inputs:** {', '.join(str(p) for p in input_paths)}\n")
    report.append(f"**Portfolio:** {total_trades} trades, total_R={portfolio_r:.2f}, E[R]={portfolio_e:.4f}\n")
    report.append(f"**Verdict counts:** {verdict_counts}\n")
    report.append(CLASSIFY_RULES + "\n")
    def _to_md(df: pd.DataFrame) -> str:
        if df.empty:
            return "_(empty)_"
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
        return "\n".join(lines)

    report.append("## Per-playbook results\n")
    report.append(_to_md(stats))
    report.append("\n")

    for verdict in ("PROMOTE", "CALIBRATE", "KILL", "QUARANTINE"):
        subset = stats[stats["verdict"] == verdict]
        if subset.empty:
            continue
        report.append(f"\n## {verdict} ({len(subset)} playbooks)\n")
        report.append(_to_md(subset))
        report.append("\n")

    out_text = "\n".join(report)
    if args.output:
        Path(args.output).write_text(out_text)
        print(f"Wrote {args.output}")
    else:
        print(out_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
