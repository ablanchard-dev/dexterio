from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_require_safe_layout_token_rejects_slashes() -> None:
    from jobs.backtest_jobs import _require_safe_layout_token

    _require_safe_layout_token("output_parent", "ui_wf_ok_20260415")
    with pytest.raises(ValueError):
        _require_safe_layout_token("output_parent", "ui/wf/bad")


def test_walk_forward_worker_writes_pointer_and_copies_campaign_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from jobs import backtest_jobs

    # Force all on-disk writes under tmp_path, not the real repo results.
    results_root = tmp_path / "results_root"

    def fake_results_path(*parts: str) -> Path:
        p = results_root.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    import utils.path_resolver as path_resolver

    monkeypatch.setattr(path_resolver, "results_path", fake_results_path)

    job_dir = tmp_path / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = tmp_path / "job.log"

    monkeypatch.setattr(backtest_jobs, "get_job_dir", lambda job_id: job_dir)
    monkeypatch.setattr(backtest_jobs, "get_job_log", lambda job_id: log_path)

    calls: list[tuple[str, dict]] = []

    def _record_update(job_id: str, status: str, **kwargs):
        calls.append((status, kwargs))

    monkeypatch.setattr(backtest_jobs, "update_job_status", _record_update)

    # Avoid depending on rollup internals in this unit test.
    import utils.campaign_rollup as campaign_rollup

    monkeypatch.setattr(
        campaign_rollup,
        "rollup_summaries_under_base",
        lambda base, logical_name: {"run_count": 2, "total_trades_sum": 123, "expectancy_r_weighted_by_trades": 0.1},
    )

    # Fake subprocess: create expected canonical outputs.
    class _Proc:
        def __init__(self, returncode: int):
            self.returncode = returncode

    def fake_run(cmd, cwd=None, stdout=None, stderr=None):
        # Create canonical campaign root outputs.
        output_parent = cmd[cmd.index("--output-parent") + 1] if "--output-parent" in cmd else "ui_wf_test_20260416"
        campaign_root = fake_results_path("labs", "mini_week", output_parent)
        campaign_root.mkdir(parents=True, exist_ok=True)

        if any(str(x).endswith("run_walk_forward_mini_lab.py") for x in cmd):
            (campaign_root / "walk_forward_campaign.json").write_text(
                json.dumps({"schema_version": "WalkForwardCampaignV0"}), encoding="utf-8"
            )
            return _Proc(0)

        if any(str(x).endswith("audit_campaign_output_parent.py") for x in cmd):
            out_idx = cmd.index("--out") + 1
            Path(cmd[out_idx]).write_text(json.dumps({"schema_version": "CampaignAuditV0"}), encoding="utf-8")
            return _Proc(0)

        if any(str(x).endswith("rollup_campaign_summaries.py") for x in cmd):
            out_idx = cmd.index("--out") + 1
            Path(cmd[out_idx]).write_text(json.dumps({"schema_version": "CampaignRollupV0"}), encoding="utf-8")
            return _Proc(0)

        return _Proc(0)

    import subprocess

    monkeypatch.setattr(subprocess, "run", fake_run)

    job_id = "abc12345"
    req = {
        "protocol": "MINI_LAB_WALK_FORWARD",
        "symbols": ["SPY"],
        "start_date": "2025-11-01",
        "end_date": "2025-11-08",
        "trading_mode": "AGGRESSIVE",
        "trade_types": ["DAILY", "SCALP"],
        "output_parent": "ui_wf_test_20260416",
        "label_prefix": "wf",
    }

    backtest_jobs.run_mini_lab_walk_forward_worker(job_id, req)

    # Ensure a pointer was written and final status is done.
    pointer = json.loads((job_dir / "campaign_pointer.json").read_text(encoding="utf-8"))
    assert pointer["job_id"] == job_id
    assert pointer["output_parent"] == "ui_wf_test_20260416"
    assert pointer["label_prefix"] == "wf"
    assert "campaign_root" in pointer

    # Ensure the job dir received downloadable copies.
    assert (job_dir / "walk_forward_campaign.json").is_file()
    assert (job_dir / "campaign_audit.json").is_file()
    assert (job_dir / "campaign_rollup.json").is_file()

    assert calls and calls[-1][0] == "done"
