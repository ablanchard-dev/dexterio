"""
Verdict gate campagne backtest → paper (hors moteur, lecture JSON only).

Verdicts (chaînes stables pour CI / scripts) :
- NOT_READY
- BACKTEST_READY_BUT_NOT_PAPER_READY
- LIMITED_PAPER_READY_IF_SCOPE_REDUCED
- LIMITED_PAPER_READY_WITH_PLAYBOOK_SET_AGGRESSIVE_CANONICAL
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Playbooks autorisés pour le verdict « noyau AGGRESSIVE canon » (sans YAML dérivé).
# Source : engines/risk_engine.AGGRESSIVE_ALLOWLIST (dupliqué volontairement pour éviter import lourd).
AGGRESSIVE_CANONICAL_PLAYBOOK_SET: tuple[str, ...] = (
    "News_Fade",
    "Session_Open_Scalp",
    "NY_Open_Reversal",
    "Morning_Trap_Reversal",
    "Liquidity_Sweep_Scalp",
    "FVG_Fill_Scalp",
)


def load_json(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def compute_campaign_gate_verdict(
    summary: Dict[str, Any],
    manifest: Optional[Dict[str, Any]] = None,
    *,
    require_manifest_coverage: bool = False,
    require_trade_metrics: bool = False,
) -> Dict[str, Any]:
    """
    Agrège des checks déclaratifs. Ne prétend pas valider la stratégie : seulement la **traçabilité** minimale.
    """
    checks: List[Dict[str, Any]] = []
    reasons: List[str] = []
    paper_blockers: List[str] = []

    dc = summary.get("data_coverage_ok")
    checks.append({"id": "summary.data_coverage_ok", "ok": dc is True})
    if dc is not True:
        reasons.append("mini_lab_summary.data_coverage_ok n'est pas true (run sans preflight manifest ou données incomplètes)")

    if require_manifest_coverage and manifest:
        block = manifest.get("data_coverage") or {}
        mc = block.get("coverage_ok")
        checks.append({"id": "manifest.data_coverage.coverage_ok", "ok": mc is True})
        if mc is not True:
            reasons.append("run_manifest.data_coverage.coverage_ok n'est pas true")
        if summary.get("run_id") != manifest.get("run_id"):
            checks.append({"id": "manifest.run_id_matches_summary", "ok": False})
            reasons.append("run_id summary vs manifest incohérent")
        else:
            checks.append({"id": "manifest.run_id_matches_summary", "ok": True})
    elif require_manifest_coverage and not manifest:
        checks.append({"id": "manifest.present", "ok": False})
        reasons.append("manifest requis mais absent")

    if require_trade_metrics:
        tm = summary.get("trade_metrics_parquet")
        ok_tm = isinstance(tm, dict) and tm.get("schema_version") == "MiniLabTradeMetricsParquetV0"
        checks.append({"id": "summary.trade_metrics_parquet", "ok": ok_tm})
        if not ok_tm:
            reasons.append("trade_metrics_parquet absent ou schéma inattendu")

    if summary.get("playbooks_yaml"):
        paper_blockers.append(
            "playbooks_yaml non null : campagne YAML dérivée — hors noyau canon pour paper limité standard"
        )

    if summary.get("respect_allowlists") is False:
        paper_blockers.append("respect_allowlists=false : cadre non comparable au noyau policy")

    verdict: str
    if reasons:
        verdict = "NOT_READY"
    elif paper_blockers:
        verdict = "BACKTEST_READY_BUT_NOT_PAPER_READY"
    elif require_trade_metrics:
        verdict = "LIMITED_PAPER_READY_IF_SCOPE_REDUCED"
    else:
        verdict = "BACKTEST_READY_BUT_NOT_PAPER_READY"

    # Noyau AGGRESSIVE canon : uniquement si déjà « prêt limité » et pas de YAML dérivé + allowlists OK
    if (
        verdict == "LIMITED_PAPER_READY_IF_SCOPE_REDUCED"
        and not paper_blockers
        and summary.get("respect_allowlists") is True
        and not summary.get("playbooks_yaml")
    ):
        verdict = "LIMITED_PAPER_READY_WITH_PLAYBOOK_SET_AGGRESSIVE_CANONICAL"

    return {
        "schema_version": "CampaignGateVerdictV0",
        "verdict": verdict,
        "reasons": reasons,
        "paper_blockers": paper_blockers,
        "checks": checks,
        "reference_playbook_set": list(AGGRESSIVE_CANONICAL_PLAYBOOK_SET),
        "note": "Verdict documentaire — décision produit finale reste humaine (NF gate, Wave2, etc.).",
    }


def verdict_from_paths(
    summary_path: Path | str,
    manifest_path: Optional[Path | str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    s = load_json(summary_path)
    m = load_json(manifest_path) if manifest_path else None
    return compute_campaign_gate_verdict(s, m, **kwargs)
