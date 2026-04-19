#!/usr/bin/env python3
"""Phase B0.4 — build calib_corpus_v1 (production-like corpus for B1 calibration).

Runs 4 weeks (jun_w3 + aug_w3 + oct_w2 + nov_w4) with:
  - RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true   (bypass denylist)
  - RISK_EVAL_RELAX_CAPS=false           (caps ACTIVE: cooldown 5min + 10/session)
  - RISK_EVAL_DISABLE_KILL_SWITCH=true   (avoid circuit-breaker truncation)
  - RISK_EVAL_CALIB_ALLOWLIST=<subset>   (restrict to B1 candidates)

Default allowlist: 4 CALIBRATE targets (SCALP_Aplus_1 excluded — B0.1a verdict=SPAM).
Output dir: results/labs/mini_week/calib_corpus_v1/

Manifest (required fields per plan B0.4 gate):
  git_sha, env_flags, allowlist_exact, period, playbooks_included, caps_config

Usage:
  python backend/scripts/build_calib_corpus.py
  python backend/scripts/build_calib_corpus.py --skip-existing
  python backend/scripts/build_calib_corpus.py --playbooks "Morning_Trap_Reversal,Engulfing_Bar_V056"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path


# Matches fair audit windows used in Phase A verdict
WINDOWS = [
    ("2025-06-16", "2025-06-20", "jun_w3"),
    ("2025-08-18", "2025-08-22", "aug_w3"),
    ("2025-10-06", "2025-10-10", "oct_w2"),
    ("2025-11-17", "2025-11-21", "nov_w4"),
]

# B1 candidates per approved plan — SCALP_Aplus_1 excluded (B0.1a SPAM verdict)
DEFAULT_ALLOWLIST = [
    "Morning_Trap_Reversal",
    "Engulfing_Bar_V056",
    "BOS_Scalp_1m",
    "Liquidity_Sweep_Scalp",
]

OUTPUT_PARENT = "calib_corpus_v1"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(backend_dir), text=True
        ).strip()
    except Exception:
        return "unknown"


def _run_week(start: str, end: str, label: str, allowlist_csv: str, skip_existing: bool) -> int:
    week_script = backend_dir / "scripts" / "run_mini_lab_week.py"
    out_dir = Path(results_path("labs", "mini_week", OUTPUT_PARENT, label))
    summary_path = out_dir / f"mini_lab_summary_{OUTPUT_PARENT}_{label}.json"
    if skip_existing and summary_path.is_file():
        print(f"[calib_corpus] skip existing {label}")
        return 0
    cmd = [
        sys.executable,
        str(week_script),
        "--start", start,
        "--end", end,
        "--label", label,
        "--symbols", "SPY,QQQ",
        "--output-parent", OUTPUT_PARENT,
        "--no-respect-allowlists",
        "--no-relax-caps",
        "--calib-allowlist", allowlist_csv,
    ]
    print(f"[calib_corpus] RUN {label} {start}..{end}")
    r = subprocess.run(cmd, cwd=str(backend_dir))
    return r.returncode


def _collect_trade_counts(allowlist: List[str]) -> Dict[str, int]:
    root = Path(results_path("labs", "mini_week", OUTPUT_PARENT))
    counts: Dict[str, int] = {pb: 0 for pb in allowlist}
    for label_dir in sorted(root.iterdir() if root.exists() else []):
        if not label_dir.is_dir():
            continue
        for p in label_dir.glob("trades_*.parquet"):
            df = pd.read_parquet(p, columns=["playbook"])
            for pb, n in df["playbook"].value_counts().items():
                counts[pb] = counts.get(pb, 0) + int(n)
    return counts


def _inter_trade_gap_p50(allowlist: List[str]) -> Dict[str, float]:
    root = Path(results_path("labs", "mini_week", OUTPUT_PARENT))
    dfs: List[pd.DataFrame] = []
    for label_dir in sorted(root.iterdir() if root.exists() else []):
        if not label_dir.is_dir():
            continue
        for p in label_dir.glob("trades_*.parquet"):
            dfs.append(pd.read_parquet(p, columns=["timestamp_entry", "symbol", "playbook"]))
    if not dfs:
        return {}
    df = pd.concat(dfs, ignore_index=True)
    df["timestamp_entry"] = pd.to_datetime(df["timestamp_entry"], utc=True)
    out: Dict[str, float] = {}
    for pb in allowlist:
        grp = df[df["playbook"] == pb].sort_values(["symbol", "timestamp_entry"])
        if len(grp) < 2:
            out[pb] = None
            continue
        deltas = grp.groupby("symbol")["timestamp_entry"].diff().dropna()
        if deltas.empty:
            out[pb] = None
        else:
            out[pb] = float(deltas.dt.total_seconds().quantile(0.50))
    return out


def _write_manifest(allowlist: List[str], period_start: str, period_end: str) -> Path:
    root = Path(results_path("labs", "mini_week", OUTPUT_PARENT))
    root.mkdir(parents=True, exist_ok=True)
    trade_counts = _collect_trade_counts(allowlist)
    gap_p50 = _inter_trade_gap_p50(allowlist)
    manifest = {
        "schema_version": "CalibCorpusV1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "env_flags": {
            "RISK_EVAL_ALLOW_ALL_PLAYBOOKS": "true",
            "RISK_EVAL_RELAX_CAPS": "false",
            "RISK_EVAL_DISABLE_KILL_SWITCH": "true",
            "RISK_EVAL_CALIB_ALLOWLIST": ",".join(allowlist),
        },
        "allowlist_exact": sorted(allowlist),
        "period": {
            "start_date": period_start,
            "end_date": period_end,
            "windows": [
                {"start": s, "end": e, "label": label} for s, e, label in WINDOWS
            ],
        },
        "playbooks_included": {pb: {"trades": trade_counts.get(pb, 0),
                                      "inter_trade_gap_p50_sec": gap_p50.get(pb)}
                                for pb in sorted(allowlist)},
        "caps_config": {
            "cooldown_minutes_aggressive": 5,
            "session_cap_aggressive": 10,
            "note": "Values from risk_engine.COOLDOWN_MINUTES_AGGRESSIVE + AGGRESSIVE_MAX_TRADES_PER_SESSION_PLAYBOOK",
        },
        "gates": {
            "min_trades_per_playbook": 20,
            "trades_per_playbook_ok": all(trade_counts.get(pb, 0) >= 20 for pb in allowlist),
            "gap_p50_respects_cooldown": all(
                gap_p50.get(pb) is None or gap_p50.get(pb) >= 300
                for pb in allowlist
            ),
        },
    }
    out = root / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--playbooks", type=str, default=",".join(DEFAULT_ALLOWLIST),
                    help="CSV of B1 candidate playbooks")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--manifest-only", action="store_true",
                    help="Only regenerate manifest.json from existing runs")
    args = ap.parse_args()

    allowlist = [s.strip() for s in args.playbooks.split(",") if s.strip()]

    if not args.manifest_only:
        for start, end, label in WINDOWS:
            rc = _run_week(start, end, label, ",".join(allowlist), args.skip_existing)
            if rc != 0:
                print(f"[calib_corpus] FAIL {label} exit={rc}", file=sys.stderr)
                return rc

    period_start = min(s for s, _, _ in WINDOWS)
    period_end = max(e for _, e, _ in WINDOWS)
    manifest_path = _write_manifest(allowlist, period_start, period_end)
    manifest = json.loads(manifest_path.read_text())
    print(f"\n[calib_corpus] Wrote {manifest_path}")
    print(json.dumps(manifest["playbooks_included"], indent=2))
    print(f"Gates: {manifest['gates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
