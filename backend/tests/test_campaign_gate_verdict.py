"""Verdict gate campagne (lecture JSON)."""
from __future__ import annotations

from utils.campaign_gate_verdict import compute_campaign_gate_verdict


def test_not_ready_missing_coverage() -> None:
    r = compute_campaign_gate_verdict({"run_id": "x", "data_coverage_ok": False})
    assert r["verdict"] == "NOT_READY"


def test_backtest_ready_blockers_yaml() -> None:
    s = {
        "run_id": "x",
        "data_coverage_ok": True,
        "playbooks_yaml": "/tmp/derived.yml",
        "respect_allowlists": True,
        "trade_metrics_parquet": {"schema_version": "MiniLabTradeMetricsParquetV0"},
    }
    r = compute_campaign_gate_verdict(s, require_trade_metrics=True)
    assert r["verdict"] == "BACKTEST_READY_BUT_NOT_PAPER_READY"
    assert r["paper_blockers"]


def test_limited_paper_canonical() -> None:
    s = {
        "run_id": "x",
        "data_coverage_ok": True,
        "respect_allowlists": True,
        "playbooks_yaml": None,
        "trade_metrics_parquet": {"schema_version": "MiniLabTradeMetricsParquetV0"},
    }
    r = compute_campaign_gate_verdict(s, require_trade_metrics=True)
    assert r["verdict"] == "LIMITED_PAPER_READY_WITH_PLAYBOOK_SET_AGGRESSIVE_CANONICAL"


def test_manifest_mismatch_run_id() -> None:
    s = {"run_id": "a", "data_coverage_ok": True}
    m = {"run_id": "b", "data_coverage": {"coverage_ok": True}}
    r = compute_campaign_gate_verdict(s, m, require_manifest_coverage=True)
    assert r["verdict"] == "NOT_READY"
