#!/usr/bin/env python3
"""Phase B2.2 — compare pre-calibration (B0.4 calib_corpus_v1) vs post-patch corpus.

Reads trades parquets from two corpora and reports per-playbook deltas on
E[R], WR, trade count, time_stop ratio, avg peak_R, avg |mae_r|.

Usage:
  python backend/scripts/compare_calibration.py \
    --before backend/results/labs/mini_week/calib_corpus_v1 \
    --after  backend/results/labs/mini_week/b2_morningtrap_v1 \
    --output backend/data/backtest_results/b2_morningtrap_verdict.md
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


def _load_parquets(root: Path) -> pd.DataFrame:
    frames = []
    for p in sorted(root.rglob("trades_*.parquet")):
        try:
            frames.append(pd.read_parquet(p))
        except Exception as e:
            print(f"WARN: cannot read {p}: {e}", file=sys.stderr)
    if not frames:
        raise SystemExit(f"No trades parquet under {root}")
    return pd.concat(frames, ignore_index=True)


def _metrics(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"n": 0, "wins": 0, "wr": None, "er": None,
                "time_stop_pct": None, "avg_peak_r": None, "avg_abs_mae_r": None,
                "total_r": None}
    wins = int((df["outcome"] == "win").sum())
    r = pd.to_numeric(df["r_multiple"], errors="coerce")
    peak = pd.to_numeric(df.get("peak_r"), errors="coerce") if "peak_r" in df.columns else None
    mae = pd.to_numeric(df.get("mae_r"), errors="coerce") if "mae_r" in df.columns else None
    exit_col = df.get("exit_reason")
    time_stop = int((exit_col == "time_stop").sum()) if exit_col is not None else 0
    return {
        "n": n,
        "wins": wins,
        "wr": round(100.0 * wins / n, 1),
        "er": round(float(r.mean()), 3) if r.notna().any() else None,
        "time_stop_pct": round(100.0 * time_stop / n, 1),
        "avg_peak_r": round(float(peak.mean()), 2) if peak is not None and peak.notna().any() else None,
        "avg_abs_mae_r": round(float(mae.abs().mean()), 2) if mae is not None and mae.notna().any() else None,
        "total_r": round(float(r.sum()), 2) if r.notna().any() else None,
    }


def _fmt(x, na="—"):
    return na if x is None else x


def _diff(before, after, key, sign_flip=False):
    b = before.get(key)
    a = after.get(key)
    if b is None or a is None:
        return "—"
    d = a - b
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "=")
    if sign_flip:
        # for metrics where down=better (time_stop, |mae_r|)
        arrow = "↓" if d < 0 else ("↑" if d > 0 else "=")
    return f"{d:+.3f} {arrow}" if isinstance(d, float) else f"{d:+} {arrow}"


def _playbook_set(df_b: pd.DataFrame, df_a: pd.DataFrame) -> list:
    pb = set(df_b["playbook"].unique()) | set(df_a["playbook"].unique())
    return sorted(pb)


def _exit_mix(df: pd.DataFrame) -> dict:
    if "exit_reason" not in df.columns or df.empty:
        return {}
    counts = df["exit_reason"].value_counts().to_dict()
    total = sum(counts.values())
    return {k: round(100.0 * v / total, 1) for k, v in counts.items()}


def _build_report(before: pd.DataFrame, after: pd.DataFrame,
                  before_path: Path, after_path: Path) -> str:
    lines: List[str] = []
    lines.append(f"# B2 comparison — {after_path.name} vs {before_path.name}")
    lines.append("")
    lines.append(f"**Before**: `{before_path}` — {len(before)} trades")
    lines.append(f"**After**: `{after_path}` — {len(after)} trades")
    lines.append("")

    lines.append("## Per-playbook delta")
    lines.append("")
    lines.append("| playbook | n (B→A) | WR% (B→A) | E[R] (B→A, Δ) | time_stop% (B→A) | avg peak_R (B→A) | avg |mae_r| (B→A) | total_R (B→A) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for pb in _playbook_set(before, after):
        mb = _metrics(before[before["playbook"] == pb])
        ma = _metrics(after[after["playbook"] == pb])
        er_delta = _diff(mb, ma, "er")
        lines.append(
            f"| {pb} "
            f"| {mb['n']} → {ma['n']} "
            f"| {_fmt(mb['wr'])} → {_fmt(ma['wr'])} "
            f"| {_fmt(mb['er'])} → {_fmt(ma['er'])} ({er_delta}) "
            f"| {_fmt(mb['time_stop_pct'])} → {_fmt(ma['time_stop_pct'])} "
            f"| {_fmt(mb['avg_peak_r'])} → {_fmt(ma['avg_peak_r'])} "
            f"| {_fmt(mb['avg_abs_mae_r'])} → {_fmt(ma['avg_abs_mae_r'])} "
            f"| {_fmt(mb['total_r'])} → {_fmt(ma['total_r'])} |"
        )
    lines.append("")

    lines.append("## Exit mix delta")
    lines.append("")
    for pb in _playbook_set(before, after):
        eb = _exit_mix(before[before["playbook"] == pb])
        ea = _exit_mix(after[after["playbook"] == pb])
        keys = sorted(set(eb) | set(ea))
        lines.append(f"### {pb}")
        lines.append(f"- Before: {', '.join(f'{k}={eb.get(k, 0.0)}%' for k in keys) if keys else 'n/a'}")
        lines.append(f"- After:  {', '.join(f'{k}={ea.get(k, 0.0)}%' for k in keys) if keys else 'n/a'}")
        lines.append("")

    lines.append("## Verdict (auto)")
    lines.append("")
    for pb in _playbook_set(before, after):
        mb = _metrics(before[before["playbook"] == pb])
        ma = _metrics(after[after["playbook"] == pb])
        if mb["er"] is None or ma["er"] is None:
            verdict = "insufficient data"
        elif mb["er"] < 0 and ma["er"] >= 0:
            verdict = "**✓ FIXED** — E[R] crossed to ≥0"
        elif ma["er"] > mb["er"]:
            verdict = "partial improvement (E[R] up, still negative)" if ma["er"] < 0 else "improved"
        elif ma["er"] < mb["er"]:
            verdict = "**✗ REGRESSED** — E[R] fell"
        else:
            verdict = "no change"
        lines.append(f"- **{pb}**: {verdict} (n={mb['n']}→{ma['n']}, E[R] {_fmt(mb['er'])}→{_fmt(ma['er'])})")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, type=Path)
    ap.add_argument("--after", required=True, type=Path)
    ap.add_argument("--output", type=Path, default=Path("backend/data/backtest_results/b2_comparison.md"))
    args = ap.parse_args()

    before = _load_parquets(args.before)
    after = _load_parquets(args.after)
    report = _build_report(before, after, args.before, args.after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    print(f"Wrote {args.output}")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
