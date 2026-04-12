#!/usr/bin/env python3
"""
Smoke tests outils campagne backtest (pytest ciblé, rapide, sans run long).

Usage (depuis backend/) :
  .venv/bin/python scripts/backtest_campaign_smoke.py

Optionnel : `DEXTERIO_CAMPAIGN_SMOKE_PREFLIGHT=1` lance aussi preflight sur une fenêtre
courte si `data/historical/1m/SPY.parquet` existe (nécessite dates valides en local).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent

TESTS = [
    "tests/test_backtest_data_coverage.py",
    "tests/test_backtest_campaign_tools.py",
    "tests/test_campaign_gate_verdict.py",
    "tests/test_campaign_output_audit.py",
    "tests/test_campaign_rollup.py",
]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", *TESTS]
    r = subprocess.call(cmd, cwd=str(backend_dir))
    if r != 0:
        return r

    if os.environ.get("DEXTERIO_CAMPAIGN_SMOKE_PREFLIGHT", "").strip().lower() in {"1", "true", "yes"}:
        from utils.path_resolver import historical_data_path

        spy = historical_data_path("1m", "SPY.parquet")
        if not spy.is_file():
            print("[smoke] skip preflight (no SPY parquet)", flush=True)
            return 0
        pre = [
            sys.executable,
            str(backend_dir / "scripts" / "backtest_data_preflight.py"),
            "--start",
            os.environ.get("DEXTERIO_SMOKE_PREFLIGHT_START", "2025-11-03"),
            "--end",
            os.environ.get("DEXTERIO_SMOKE_PREFLIGHT_END", "2025-11-09"),
            "--warmup-days",
            "30",
            "--ignore-warmup-check",
        ]
        print("[smoke] preflight:", " ".join(pre), flush=True)
        return subprocess.call(pre, cwd=str(backend_dir))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
