"""Validation RunSummaryV0 sur artefacts réels."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.run_summary_v0 import RunSummaryV0, parse_run_summary_v0

_BACKEND = Path(__file__).resolve().parent.parent
_BASELINE_SUMMARY = _BACKEND / "results" / "labs" / "mini_week" / "202511_w01" / "mini_lab_summary_202511_w01.json"


@pytest.mark.skipif(not _BASELINE_SUMMARY.is_file(), reason="artefact baseline absent")
def test_parse_baseline_mini_lab_summary_202511_w01() -> None:
    data = json.loads(_BASELINE_SUMMARY.read_text(encoding="utf-8"))
    m = parse_run_summary_v0(data)
    assert isinstance(m, RunSummaryV0)
    assert m.run_id == "miniweek_202511_w01"
    assert "NY_Open_Reversal" in m.funnel
    assert m.funnel["News_Fade"].trades >= 0


def test_parse_minimal_synthetic_summary() -> None:
    payload = {
        "protocol": "MINI_LAB_WEEK",
        "runner": "run_mini_lab_week.py",
        "git_sha": "abc",
        "run_id": "miniweek_test",
        "start_date": "2025-01-01",
        "end_date": "2025-01-07",
        "symbols": ["SPY"],
        "respect_allowlists": True,
        "bypass_lss_quarantine": True,
        "total_trades": 1,
        "final_capital": "100.0",
        "funnel": {
            "NY_Open_Reversal": {"matches": 1, "setups_created": 1, "after_risk": 1, "trades": 0},
            "News_Fade": {"matches": 0, "setups_created": 0, "after_risk": 0, "trades": 0},
            "Liquidity_Sweep_Scalp": {"matches": 0, "setups_created": 0, "after_risk": 0, "trades": 0},
            "FVG_Fill_Scalp": {"matches": 0, "setups_created": 0, "after_risk": 0, "trades": 0},
            "Session_Open_Scalp": {"matches": 0, "setups_created": 0, "after_risk": 0, "trades": 0},
        },
        "contract_version": "RunSummaryV0",
        "run_started_at_utc": "2026-01-01T00:00:00+00:00",
    }
    m = parse_run_summary_v0(payload)
    assert m.contract_version == "RunSummaryV0"
