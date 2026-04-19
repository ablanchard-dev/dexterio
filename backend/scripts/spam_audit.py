#!/usr/bin/env python3
"""Phase B0.1a — spam audit read-only on fair audit parquets.

Quantifies how much of the trade volume for SCALP_Aplus_1 and DAY_Aplus_1
would be blocked in production (cooldown 5 min + session cap 10/playbook)
but was permitted here by `RISK_EVAL_RELAX_CAPS=true`.

Reads existing trades_*.parquet from the 4 fair audits. No re-run.

Verdict per playbook:
  SPAM               : >50% of trades would be blocked by prod caps
  LEGITIMATE_VOLUME  : <=20% blocked
  BORDERLINE         : 20-50% blocked

Usage:
  python backend/scripts/spam_audit.py
  python backend/scripts/spam_audit.py --playbooks SCALP_Aplus_1,DAY_Aplus_1
  python backend/scripts/spam_audit.py --cooldown-min 5 --session-cap 10
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path


DEFAULT_TARGETS = [
    "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open",
    "DAY_Aplus_1_Liquidity_Sweep_OB_Retest",
]

DEFAULT_LABELS = ["fair_jun_w3", "fair_aug_w3", "fair_oct_w2", "fair_nov_w4"]


def _load_trades(labels: List[str]) -> pd.DataFrame:
    root = Path(results_path("labs", "mini_week"))
    frames = []
    for label in labels:
        for p in sorted((root / label).glob("trades_*.parquet")):
            df = pd.read_parquet(p)
            df["_label"] = label
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["timestamp_entry"] = pd.to_datetime(out["timestamp_entry"], utc=True)
    out["timestamp_exit"] = pd.to_datetime(out["timestamp_exit"], utc=True)
    return out


def _session_cap_blocks(group: pd.DataFrame, session_cap: int) -> int:
    """Count trades that exceed `session_cap` per (date, symbol, playbook, session)."""
    if group.empty:
        return 0
    keys = ["date", "symbol", "playbook", "session_label"]
    ordered = group.sort_values("timestamp_entry")
    counts = ordered.groupby(keys).cumcount()
    return int((counts >= session_cap).sum())


def _cooldown_blocks(group: pd.DataFrame, cooldown_min: int) -> Tuple[int, int]:
    """
    Count trades that would be blocked by a per (symbol, playbook) cooldown,
    using a greedy allow/block walk (first trade always allowed).

    Returns (blocked, re_entry_after_sl).
    """
    if group.empty:
        return 0, 0
    blocked = 0
    re_entry_after_sl = 0
    sorted_grp = group.sort_values("timestamp_entry")
    last_allowed_exit_by_key: Dict[Tuple[str, str], pd.Timestamp] = {}
    last_allowed_outcome_by_key: Dict[Tuple[str, str], str] = {}
    cooldown = pd.Timedelta(minutes=cooldown_min)
    for row in sorted_grp.itertuples(index=False):
        key = (row.symbol, row.playbook)
        entry = row.timestamp_entry
        last_exit = last_allowed_exit_by_key.get(key)
        if last_exit is not None and entry - last_exit < cooldown:
            blocked += 1
            last_outcome = last_allowed_outcome_by_key.get(key, "")
            if last_outcome == "loss":
                re_entry_after_sl += 1
            continue
        last_allowed_exit_by_key[key] = row.timestamp_exit
        last_allowed_outcome_by_key[key] = row.outcome
    return blocked, re_entry_after_sl


def _inter_trade_gaps(group: pd.DataFrame) -> Dict[str, float]:
    if len(group) < 2:
        return {"p5_sec": None, "p50_sec": None, "p95_sec": None, "count_pairs": 0}
    sorted_grp = group.sort_values(["symbol", "playbook", "timestamp_entry"])
    deltas = sorted_grp.groupby(["symbol", "playbook"])["timestamp_entry"].diff().dropna()
    secs = deltas.dt.total_seconds()
    if secs.empty:
        return {"p5_sec": None, "p50_sec": None, "p95_sec": None, "count_pairs": 0}
    return {
        "p5_sec": float(secs.quantile(0.05)),
        "p50_sec": float(secs.quantile(0.50)),
        "p95_sec": float(secs.quantile(0.95)),
        "pct_under_cooldown": float((secs < 300).mean()),
        "count_pairs": int(len(secs)),
    }


def _dedup_violations(group: pd.DataFrame) -> int:
    """Same (symbol, playbook, timestamp_entry) appearing more than once."""
    if group.empty:
        return 0
    dup = group.duplicated(subset=["symbol", "playbook", "timestamp_entry"], keep=False)
    return int(dup.sum())


def _audit_playbook(df: pd.DataFrame, playbook: str, cooldown_min: int, session_cap: int) -> Dict[str, Any]:
    grp = df[df["playbook"] == playbook].copy()
    total = len(grp)
    if total == 0:
        return {"playbook": playbook, "trades": 0, "verdict": "NO_DATA"}

    cooldown_blocked, re_entry_after_sl = _cooldown_blocks(grp, cooldown_min)
    session_cap_blocked = _session_cap_blocks(grp, session_cap)
    gaps = _inter_trade_gaps(grp)
    dupes = _dedup_violations(grp)

    combined_blocked = max(cooldown_blocked, session_cap_blocked)
    pct_blocked = combined_blocked / total if total else 0.0

    if pct_blocked > 0.50:
        verdict = "SPAM"
    elif pct_blocked <= 0.20:
        verdict = "LEGITIMATE_VOLUME"
    else:
        verdict = "BORDERLINE"

    return {
        "playbook": playbook,
        "trades": total,
        "cooldown_blocked": cooldown_blocked,
        "cooldown_blocked_pct": round(cooldown_blocked / total, 4),
        "session_cap_blocked": session_cap_blocked,
        "session_cap_blocked_pct": round(session_cap_blocked / total, 4),
        "combined_blocked": combined_blocked,
        "combined_blocked_pct": round(pct_blocked, 4),
        "re_entry_after_sl": re_entry_after_sl,
        "re_entry_after_sl_pct": round(re_entry_after_sl / total, 4),
        "dedup_violations": dupes,
        "inter_trade_gaps_sec": gaps,
        "trades_per_hour_avg": round(total / max(1, len(grp["date"].unique()) * 6.5), 2),
        "verdict": verdict,
    }


def _render_markdown(results: List[Dict[str, Any]], cooldown_min: int, session_cap: int) -> str:
    lines = [
        "# Phase B0.1a — Spam Audit (read-only)",
        "",
        f"**Params:** cooldown={cooldown_min}min, session_cap={session_cap}/playbook/session.",
        "**Source:** fair_* parquets (RISK_EVAL_RELAX_CAPS=true).",
        "",
        "## Verdict per playbook",
        "",
        "| playbook | trades | cooldown_blocked | session_cap_blocked | combined_blocked % | re_entry_after_sl % | p50_gap_sec | p95_gap_sec | pct_under_5min | dedup | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.get("verdict") == "NO_DATA":
            lines.append(f"| {r['playbook']} | 0 | - | - | - | - | - | - | - | - | NO_DATA |")
            continue
        g = r["inter_trade_gaps_sec"]
        p50 = f"{g['p50_sec']:.0f}" if g.get("p50_sec") is not None else "-"
        p95 = f"{g['p95_sec']:.0f}" if g.get("p95_sec") is not None else "-"
        pct_under = f"{g.get('pct_under_cooldown', 0):.1%}" if g.get("p50_sec") is not None else "-"
        lines.append(
            f"| {r['playbook']} | {r['trades']} | "
            f"{r['cooldown_blocked']} ({r['cooldown_blocked_pct']:.1%}) | "
            f"{r['session_cap_blocked']} ({r['session_cap_blocked_pct']:.1%}) | "
            f"{r['combined_blocked_pct']:.1%} | "
            f"{r['re_entry_after_sl_pct']:.1%} | {p50} | {p95} | {pct_under} | "
            f"{r['dedup_violations']} | **{r['verdict']}** |"
        )
    lines.append("")
    lines.append("## Classification")
    lines.append("- `SPAM` : >50% trades blocked by prod caps → calibration on RELAX_CAPS data invalid")
    lines.append("- `BORDERLINE` : 20-50% blocked → flag, re-run recommended with caps active")
    lines.append("- `LEGITIMATE_VOLUME` : <=20% blocked → volume is real, calibration safe")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=str, default=",".join(DEFAULT_LABELS),
                    help="Comma-separated fair audit labels (default: all 4)")
    ap.add_argument("--playbooks", type=str, default=",".join(DEFAULT_TARGETS),
                    help="Comma-separated playbook names (default: SCALP+DAY Aplus_1)")
    ap.add_argument("--cooldown-min", type=int, default=5)
    ap.add_argument("--session-cap", type=int, default=10)
    ap.add_argument("--output-md", type=str, default=None)
    ap.add_argument("--output-json", type=str, default=None)
    args = ap.parse_args()

    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    playbooks = [s.strip() for s in args.playbooks.split(",") if s.strip()]

    df = _load_trades(labels)
    if df.empty:
        print(f"No trades found for labels: {labels}", file=sys.stderr)
        return 1

    results = [_audit_playbook(df, pb, args.cooldown_min, args.session_cap) for pb in playbooks]

    md = _render_markdown(results, args.cooldown_min, args.session_cap)
    out_md = Path(args.output_md) if args.output_md else (
        backend_dir / "data" / "backtest_results" / "spam_audit_report.md"
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)

    out_json = Path(args.output_json) if args.output_json else (
        backend_dir / "data" / "backtest_results" / "spam_audit_report.json"
    )
    out_json.write_text(json.dumps({
        "params": {"cooldown_min": args.cooldown_min, "session_cap": args.session_cap, "labels": labels},
        "results": results,
    }, indent=2, default=str))

    print(md)
    print(f"\nWrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
