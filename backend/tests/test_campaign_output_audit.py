"""Audit dossiers campagne output_parent."""
from __future__ import annotations

import json
from pathlib import Path

from utils.campaign_output_audit import (
    audit_campaign_base,
    audit_output_parent,
    audit_run_subdir,
    detect_runs_under_base,
)


def test_audit_run_subdir_minimal(tmp_path: Path) -> None:
    d = tmp_path / "202511_w01"
    d.mkdir()
    (d / "mini_lab_summary_202511_w01.json").write_text(
        json.dumps(
            {
                "run_id": "x",
                "data_coverage_ok": True,
                "total_trades": 10,
                "trade_metrics_parquet": {"schema_version": "MiniLabTradeMetricsParquetV0"},
            }
        ),
        encoding="utf-8",
    )
    (d / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "x",
                "data_coverage": {"coverage_ok": True},
            }
        ),
        encoding="utf-8",
    )
    r = audit_run_subdir(d)
    assert r["data_coverage_ok_summary"] is True
    assert r["data_coverage_ok_manifest"] is True
    assert r["has_trade_metrics_parquet"] is True


def test_audit_output_parent_overall(tmp_path: Path) -> None:
    root = tmp_path / "results"
    parent = root / "labs" / "mini_week" / "camp_a"
    w1 = parent / "w1"
    w1.mkdir(parents=True)
    (w1 / "mini_lab_summary_w1.json").write_text(
        json.dumps({"run_id": "a", "data_coverage_ok": True, "total_trades": 1}),
        encoding="utf-8",
    )
    (w1 / "run_manifest.json").write_text(
        json.dumps({"run_id": "a", "data_coverage": {"coverage_ok": True}}),
        encoding="utf-8",
    )
    rep = audit_output_parent("camp_a", results_base=root)
    assert rep["schema_version"] == "CampaignOutputAuditV0"
    assert rep["run_count"] == 1
    assert rep["overall_ok"] is True


def test_detect_flat_vs_nested(tmp_path: Path) -> None:
    flat = tmp_path / "202511_w01"
    flat.mkdir()
    (flat / "mini_lab_summary_202511_w01.json").write_text(
        json.dumps({"run_id": "f", "data_coverage_ok": True, "total_trades": 1}),
        encoding="utf-8",
    )
    layout_f, rows_f = detect_runs_under_base(flat)
    assert layout_f == "flat"
    assert len(rows_f) == 1
    assert rows_f[0]["label"] == "202511_w01"

    nested_root = tmp_path / "wf_camp"
    (nested_root / "s0").mkdir(parents=True)
    (nested_root / "s0" / "mini_lab_summary_s0.json").write_text(
        json.dumps({"run_id": "n", "data_coverage_ok": True, "total_trades": 2}),
        encoding="utf-8",
    )
    layout_n, rows_n = detect_runs_under_base(nested_root)
    assert layout_n == "nested"
    assert len(rows_n) == 1
    assert rows_n[0]["label"] == "s0"


def test_audit_campaign_base_flat(tmp_path: Path) -> None:
    flat = tmp_path / "solo"
    flat.mkdir()
    (flat / "mini_lab_summary_solo.json").write_text(
        json.dumps({"run_id": "solo", "data_coverage_ok": True, "total_trades": 3}),
        encoding="utf-8",
    )
    (flat / "run_manifest.json").write_text(
        json.dumps({"run_id": "solo", "data_coverage": {"coverage_ok": True}}),
        encoding="utf-8",
    )
    rep = audit_campaign_base(flat, logical_name="solo")
    assert rep["layout"] == "flat"
    assert rep["run_count"] == 1
    assert rep["overall_ok"] is True


def test_audit_output_parent_coverage_fail(tmp_path: Path) -> None:
    root = tmp_path / "results"
    parent = root / "labs" / "mini_week" / "camp_b"
    w1 = parent / "w1"
    w1.mkdir(parents=True)
    (w1 / "mini_lab_summary_w1.json").write_text(
        json.dumps({"run_id": "a", "data_coverage_ok": False, "total_trades": 1}),
        encoding="utf-8",
    )
    (w1 / "run_manifest.json").write_text(
        json.dumps({"run_id": "a", "data_coverage": {"coverage_ok": False}}),
        encoding="utf-8",
    )
    rep = audit_output_parent("camp_b", results_base=root)
    assert rep["overall_ok"] is False
    assert "w1" in rep["labels_failed_data_coverage"]
