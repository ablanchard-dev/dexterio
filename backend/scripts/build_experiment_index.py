#!/usr/bin/env python3
"""Phase D.4 — build a JSON index of all mini_lab runs for reproducibility.

Scans `results/labs/mini_week/` for summary JSONs and produces a single
`_index.json` with run_id, git_sha, env flags, symbols, date range, and
key metrics (trades, total_R, E[R]). Rebuilds from scratch each run.

Usage:
  python scripts/build_experiment_index.py
  python scripts/build_experiment_index.py --root results/labs/mini_week
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path


def _safe_load(p: Path) -> Dict[str, Any] | None:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _find_run_dirs(root: Path) -> List[Path]:
    out = []
    for d in root.rglob("run_manifest.json"):
        out.append(d.parent)
    return out


def _run_entry(run_dir: Path) -> Dict[str, Any] | None:
    manifest = _safe_load(run_dir / "run_manifest.json") or {}
    summary_candidates = list(run_dir.glob("mini_lab_summary_*.json"))
    summary = _safe_load(summary_candidates[0]) if summary_candidates else {}
    trade_metrics = summary.get("trade_metrics") or summary.get("trade_metrics_parquet") or {}
    entry = {
        "run_id": summary.get("run_id") or manifest.get("run_id"),
        "run_dir": str(run_dir),
        "git_sha": summary.get("git_sha") or manifest.get("git_sha"),
        "run_started_at_utc": summary.get("run_started_at_utc"),
        "start_date": summary.get("start_date"),
        "end_date": summary.get("end_date"),
        "symbols": summary.get("symbols"),
        "respect_allowlists": summary.get("respect_allowlists"),
        "env_flags": (manifest.get("lab_environment") or {}).get("risk_env_flags"),
        "total_trades": summary.get("total_trades") or trade_metrics.get("trades_rows"),
        "total_r": (
            trade_metrics.get("sum_r_multiple")
            or trade_metrics.get("total_r_net")
            or (
                (trade_metrics.get("gross_profit_r") or 0.0)
                + (trade_metrics.get("gross_loss_r") or 0.0)
                if trade_metrics.get("gross_profit_r") is not None
                else None
            )
        ),
        "expectancy_r": trade_metrics.get("expectancy_r") or trade_metrics.get("mean_r_multiple"),
        "winrate": trade_metrics.get("winrate"),
        "profit_factor": trade_metrics.get("profit_factor"),
    }
    if not entry["run_id"]:
        return None
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=None, help="Root directory (default: results/labs/mini_week)")
    ap.add_argument("--output", type=str, default=None, help="Output JSON (default: <root>/_index.json)")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else Path(results_path("labs", "mini_week")).resolve()
    out = Path(args.output).expanduser().resolve() if args.output else (root / "_index.json")

    run_dirs = _find_run_dirs(root)
    entries = []
    for d in run_dirs:
        e = _run_entry(d)
        if e:
            entries.append(e)
    entries.sort(key=lambda x: x.get("run_started_at_utc") or "", reverse=True)

    payload = {
        "schema_version": "ExperimentIndexV0",
        "root": str(root),
        "count": len(entries),
        "runs": entries,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out} ({len(entries)} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
