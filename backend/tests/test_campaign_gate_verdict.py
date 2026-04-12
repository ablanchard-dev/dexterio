"""Verdict gate campagne (lecture JSON)."""
from __future__ import annotations

from utils.campaign_gate_verdict import (
    compute_campaign_gate_verdict,
    verdict_from_manifest_path,
)


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


def test_verdict_from_manifest_only_coverage_ok(tmp_path) -> None:
    import json

    m = {
        "run_id": "x",
        "respect_allowlists": True,
        "playbooks_yaml": None,
        "data_coverage": {"coverage_ok": True, "schema_version": "DataCoverageV0"},
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    r = verdict_from_manifest_path(p, require_manifest_coverage=True)
    assert r["source"] == "manifest_only"
    assert r["verdict"] == "BACKTEST_READY_BUT_NOT_PAPER_READY"


def test_manifest_mismatch_run_id() -> None:
    s = {"run_id": "a", "data_coverage_ok": True}
    m = {"run_id": "b", "data_coverage": {"coverage_ok": True}}
    r = compute_campaign_gate_verdict(s, m, require_manifest_coverage=True)
    assert r["verdict"] == "NOT_READY"
