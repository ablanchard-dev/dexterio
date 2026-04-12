"""Audit filesystem des dossiers `labs/mini_week/<output_parent>/<label>/` (hors moteur)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def audit_run_subdir(run_dir: Path) -> Dict[str, Any]:
    """
    Un sous-dossier de campagne (ex. `wf_s0_test` ou `202511_w01`).
    """
    label = run_dir.name
    row: Dict[str, Any] = {
        "label": label,
        "path": str(run_dir.resolve()),
        "summary_present": False,
        "manifest_present": False,
        "data_coverage_ok_summary": None,
        "data_coverage_ok_manifest": None,
        "total_trades": None,
        "run_id": None,
        "has_trade_metrics_parquet": False,
        "playbooks_yaml_manifest": None,
    }
    summaries = sorted(run_dir.glob("mini_lab_summary*.json"))
    if summaries:
        sp = summaries[0]
        row["summary_present"] = True
        row["summary_path"] = str(sp)
        data = _load_json(sp)
        if data:
            row["run_id"] = data.get("run_id")
            row["data_coverage_ok_summary"] = data.get("data_coverage_ok")
            row["total_trades"] = data.get("total_trades")
            tm = data.get("trade_metrics_parquet")
            row["has_trade_metrics_parquet"] = isinstance(tm, dict) and tm.get("schema_version") == (
                "MiniLabTradeMetricsParquetV0"
            )

    mf = run_dir / "run_manifest.json"
    if mf.is_file():
        row["manifest_present"] = True
        row["manifest_path"] = str(mf)
        m = _load_json(mf)
        if m:
            dc = m.get("data_coverage") or {}
            row["data_coverage_ok_manifest"] = dc.get("coverage_ok")
            row["playbooks_yaml_manifest"] = m.get("playbooks_yaml")
            if row["run_id"] is None:
                row["run_id"] = m.get("run_id")

    return row


def audit_output_parent(
    output_parent: str,
    *,
    results_base: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Parcourt `results/labs/mini_week/<output_parent>/` : chaque sous-dossier = un run.
    Si `walk_forward_campaign.json` est présent à la racine du parent, l'inclut.
    """
    if results_base is None:
        from utils.path_resolver import results_path

        base = results_path("labs", "mini_week", output_parent)
    else:
        base = results_base / "labs" / "mini_week" / output_parent

    rows: List[Dict[str, Any]] = []
    if base.is_dir():
        for sub in sorted(base.iterdir()):
            if sub.is_dir():
                rows.append(audit_run_subdir(sub))

    wf_path = base / "walk_forward_campaign.json"
    wf_block: Optional[Dict[str, Any]] = None
    if wf_path.is_file():
        raw = _load_json(wf_path)
        if raw:
            wf_block = {
                "path": str(wf_path.resolve()),
                "schema_version": raw.get("schema_version"),
                "fail_fast": raw.get("fail_fast"),
                "fail_fast_stopped": raw.get("fail_fast_stopped"),
                "max_returncode": raw.get("max_returncode"),
                "dry_run": raw.get("dry_run"),
            }

    cov_sum = [r["data_coverage_ok_summary"] is True for r in rows if r["summary_present"]]
    cov_man = [r["data_coverage_ok_manifest"] is True for r in rows if r["manifest_present"]]
    all_cov_summary = bool(rows) and cov_sum and all(cov_sum)
    all_cov_manifest = bool(rows) and cov_man and all(cov_man)

    failed_labels = [
        r["label"]
        for r in rows
        if r["summary_present"] and r["data_coverage_ok_summary"] is not True
    ]

    wf_ok = True
    if wf_block and wf_block.get("max_returncode") is not None:
        wf_ok = int(wf_block["max_returncode"]) == 0 and wf_block.get("fail_fast_stopped") is None

    return {
        "schema_version": "CampaignOutputAuditV0",
        "output_parent": output_parent,
        "base_path": str(base.resolve()) if base.exists() else str(base),
        "base_exists": base.is_dir(),
        "run_count": len(rows),
        "runs": rows,
        "walk_forward_campaign": wf_block,
        "all_data_coverage_ok_summary": all_cov_summary if rows else False,
        "all_data_coverage_ok_manifest": all_cov_manifest if rows else False,
        "labels_missing_summary": [r["label"] for r in rows if not r["summary_present"]],
        "labels_failed_data_coverage": failed_labels,
        "walk_forward_ok": wf_ok if wf_block else None,
        "overall_ok": bool(rows)
        and all_cov_summary
        and not failed_labels
        and (wf_block is None or wf_ok),
    }
