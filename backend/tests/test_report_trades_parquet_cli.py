"""Smoke CLI report_trades_parquet + paper_supervised_precheck."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

_BACKEND = Path(__file__).resolve().parent.parent
_REPORT = _BACKEND / "scripts" / "report_trades_parquet.py"
_PRECHECK = _BACKEND / "scripts" / "paper_supervised_precheck.py"
_PY = sys.executable


def test_report_trades_parquet_list_analyzers() -> None:
    r = subprocess.run(
        [_PY, str(_REPORT), "--list-analyzers"],
        cwd=str(_BACKEND),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "summary_r" in data["analyzers"]


def test_report_trades_parquet_on_temp_file(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "playbook": ["News_Fade"],
            "outcome": ["win"],
            "r_multiple": [1.0],
            "exit_reason": ["TP1"],
        }
    )
    p = tmp_path / "x.parquet"
    df.to_parquet(p, index=False)
    r = subprocess.run(
        [_PY, str(_REPORT), str(p), "--analyzers", "summary_r", "--json"],
        cwd=str(_BACKEND),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["results"]["summary_r"]["trades"] == 1


def test_paper_supervised_precheck_json() -> None:
    r = subprocess.run(
        [_PY, str(_PRECHECK), "--json"],
        cwd=str(_BACKEND),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "git_sha" in data
    assert "reminders" in data
    assert data["trades_bundle"] is None
